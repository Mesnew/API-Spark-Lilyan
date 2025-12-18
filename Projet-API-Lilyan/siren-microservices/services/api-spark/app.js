const express = require('express');
const axios = require('axios');
const mysql = require('mysql2/promise');
const swaggerUi = require('swagger-ui-express');
const swaggerJsDoc = require('swagger-jsdoc');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3002;
const OAUTH2_URL = process.env.OAUTH2_URL || 'http://oauth2:3000';

// MySQL Configuration
const dbConfig = {
  host: process.env.MYSQL_HOST || 'db',
  port: parseInt(process.env.MYSQL_PORT || '3306'),
  user: process.env.MYSQL_USER || 'sirenuser',
  password: process.env.MYSQL_PASSWORD || '',
  database: process.env.MYSQL_DATABASE || 'siren'
};

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// OAuth2 Middleware - Vérifie le token auprès du service OAuth2
async function verifyToken(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Missing or invalid Authorization header'
    });
  }

  const token = authHeader.substring(7);

  try {
    const response = await axios.get(`${OAUTH2_URL}/secure`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    req.user = response.data.user;
    next();
  } catch (error) {
    console.error('OAuth2 verification failed:', error.message);
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Invalid or expired token'
    });
  }
}

// Swagger configuration
const swaggerOptions = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'API Spark - Statistiques SIREN',
      version: '1.0.0',
      description: 'API d\'analyse statistique des entreprises SIREN via Apache Spark',
      contact: {
        name: 'API Support',
        email: 'support@example.com'
      }
    },
    servers: [
      {
        url: 'http://spark.siren.local',
        description: 'Serveur via Nginx Proxy (recommandé)'
      },
      {
        url: 'http://localhost:3002',
        description: 'Serveur de développement direct'
      },
      {
        url: 'http://api-spark:3002',
        description: 'Serveur Docker interne'
      }
    ],
    components: {
      securitySchemes: {
        BearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'Token OAuth2 obtenu depuis /oauth/token'
        }
      },
      schemas: {
        ActivityStat: {
          type: 'object',
          properties: {
            '@type': { type: 'string', example: 'AggregateRating' },
            '@id': { type: 'string', example: 'activity:62.01Z' },
            identifier: { type: 'string', example: '62.01Z' },
            ratingCount: { type: 'integer', example: 150 }
          }
        },
        ItemList: {
          type: 'object',
          properties: {
            '@context': { type: 'string', example: 'https://schema.org/' },
            '@type': { type: 'string', example: 'ItemList' },
            numberOfItems: { type: 'integer', example: 20 },
            itemListElement: {
              type: 'array',
              items: { '$ref': '#/components/schemas/ActivityStat' }
            },
            pagination: {
              type: 'object',
              properties: {
                page: { type: 'integer', example: 1 },
                limit: { type: 'integer', example: 20 },
                total: { type: 'integer', example: 100 },
                total_pages: { type: 'integer', example: 5 },
                has_next: { type: 'boolean', example: true },
                has_prev: { type: 'boolean', example: false }
              }
            }
          }
        }
      }
    },
    security: [
      {
        BearerAuth: []
      }
    ]
  },
  apis: ['./app.js']
};

const swaggerDocs = swaggerJsDoc(swaggerOptions);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerDocs));

// Helper function - Transformer les résultats en JSON-LD avec Hydra
function toJSONLD(type, data) {
  return {
    '@context': [
      'https://schema.org/',
      {
        'hydra': 'http://www.w3.org/ns/hydra/core#',
        'view': 'hydra:view',
        'first': 'hydra:first',
        'last': 'hydra:last',
        'next': 'hydra:next',
        'previous': 'hydra:previous',
        'totalItems': 'hydra:totalItems'
      }
    ],
    '@type': type,
    ...data
  };
}

// Helper function - Créer la pagination avec Hydra
function createPagination(page, limit, total, baseUrl) {
  const totalPages = Math.ceil(total / limit);
  const pagination = {
    page,
    limit,
    totalItems: total,
    total_pages: totalPages,
    has_next: page < totalPages,
    has_prev: page > 1
  };

  // Ajouter les liens Hydra
  if (baseUrl) {
    pagination.view = {
      '@id': `${baseUrl}?page=${page}&limit=${limit}`,
      '@type': 'hydra:PartialCollectionView'
    };

    if (page > 1) {
      pagination.view.first = `${baseUrl}?page=1&limit=${limit}`;
      pagination.view.previous = `${baseUrl}?page=${page - 1}&limit=${limit}`;
    }

    if (page < totalPages) {
      pagination.view.next = `${baseUrl}?page=${page + 1}&limit=${limit}`;
      pagination.view.last = `${baseUrl}?page=${totalPages}&limit=${limit}`;
    }
  }

  return pagination;
}

/**
 * @swagger
 * /health:
 *   get:
 *     summary: Health check
 *     description: Vérifie l'état de santé de l'API Spark
 *     tags: [Health]
 *     security: []
 *     responses:
 *       200:
 *         description: Service opérationnel
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 status:
 *                   type: string
 *                   example: OK
 *                 service:
 *                   type: string
 *                   example: api-spark
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    service: 'api-spark',
    version: '1.0.0',
    database: `${dbConfig.host}:${dbConfig.port}`
  });
});

/**
 * @swagger
 * /stats/activites/count:
 *   get:
 *     summary: Nombre d'entreprises par code activité
 *     description: Retourne le nombre d'entreprises groupées par code d'activité principale
 *     tags: [Statistiques]
 *     parameters:
 *       - in: query
 *         name: page
 *         schema:
 *           type: integer
 *           default: 1
 *         description: Numéro de page
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 20
 *           maximum: 100
 *         description: Nombre d'éléments par page
 *     responses:
 *       200:
 *         description: Liste des statistiques par activité
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ItemList'
 *       401:
 *         description: Non autorisé
 */
app.get('/stats/activites/count', verifyToken, async (req, res) => {
  let conn;
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    const offset = (page - 1) * limit;

    conn = await mysql.createConnection(dbConfig);

    // Compter le total
    const [countRows] = await conn.query(`
      SELECT COUNT(DISTINCT activite_principale_unite_legale) as total
      FROM unite_legale
      WHERE activite_principale_unite_legale IS NOT NULL
    `);
    const total = countRows[0].total;

    // Récupérer les données paginées
    const [rows] = await conn.query(`
      SELECT
        activite_principale_unite_legale as code,
        COUNT(siren) as count
      FROM unite_legale
      WHERE activite_principale_unite_legale IS NOT NULL
      GROUP BY activite_principale_unite_legale
      ORDER BY count DESC
      LIMIT ? OFFSET ?
    `, [limit, offset]);

    const items = rows.map(row => ({
      '@type': 'AggregateRating',
      '@id': `activity:${row.code}`,
      'identifier': row.code,
      'ratingCount': parseInt(row.count)
    }));

    const baseUrl = `${req.protocol}://${req.get('host')}/stats/activites/count`;

    const result = toJSONLD('ItemList', {
      numberOfItems: items.length,
      itemListElement: items,
      totalItems: total,
      pagination: createPagination(page, limit, total, baseUrl)
    });

    res.json(result);
  } catch (error) {
    console.error('Error in /stats/activites/count:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message
    });
  } finally {
    if (conn) await conn.end();
  }
});

/**
 * @swagger
 * /stats/activites/filter:
 *   get:
 *     summary: Filtrer les entreprises par code activité
 *     description: Retourne le nombre d'entreprises pour un code d'activité spécifique
 *     tags: [Statistiques]
 *     parameters:
 *       - in: query
 *         name: code
 *         required: true
 *         schema:
 *           type: string
 *         description: Code d'activité (ex. 62.01Z)
 *     responses:
 *       200:
 *         description: Statistique pour le code activité
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ActivityStat'
 *       400:
 *         description: Paramètre manquant
 *       401:
 *         description: Non autorisé
 */
app.get('/stats/activites/filter', verifyToken, async (req, res) => {
  let conn;
  try {
    const { code } = req.query;

    if (!code) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Parameter "code" is required'
      });
    }

    conn = await mysql.createConnection(dbConfig);

    const [rows] = await conn.query(`
      SELECT
        activite_principale_unite_legale as code,
        COUNT(siren) as count
      FROM unite_legale
      WHERE activite_principale_unite_legale = ?
      GROUP BY activite_principale_unite_legale
    `, [code]);

    if (rows.length === 0) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No data found for activity code: ${code}`
      });
    }

    const row = rows[0];
    const result = toJSONLD('AggregateRating', {
      '@id': `activity:${row.code}`,
      'identifier': row.code,
      'ratingCount': parseInt(row.count)
    });

    res.json(result);
  } catch (error) {
    console.error('Error in /stats/activites/filter:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message
    });
  } finally {
    if (conn) await conn.end();
  }
});

/**
 * @swagger
 * /stats/activites/top:
 *   get:
 *     summary: Codes activité les plus représentés
 *     description: Retourne les codes d'activité avec le plus grand nombre d'entreprises
 *     tags: [Statistiques]
 *     parameters:
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 20
 *           maximum: 100
 *         description: Nombre de résultats
 *     responses:
 *       200:
 *         description: Top des codes activité
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ItemList'
 *       401:
 *         description: Non autorisé
 */
app.get('/stats/activites/top', verifyToken, async (req, res) => {
  let conn;
  try {
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);

    conn = await mysql.createConnection(dbConfig);

    const [rows] = await conn.query(`
      SELECT
        activite_principale_unite_legale as code,
        COUNT(siren) as count
      FROM unite_legale
      WHERE activite_principale_unite_legale IS NOT NULL
      GROUP BY activite_principale_unite_legale
      ORDER BY count DESC
      LIMIT ?
    `, [limit]);

    const items = rows.map(row => ({
      '@type': 'AggregateRating',
      '@id': `activity:${row.code}`,
      'identifier': row.code,
      'ratingCount': parseInt(row.count)
    }));

    const result = toJSONLD('ItemList', {
      numberOfItems: items.length,
      totalItems: items.length,
      itemListElement: items
    });

    res.json(result);
  } catch (error) {
    console.error('Error in /stats/activites/top:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message
    });
  } finally {
    if (conn) await conn.end();
  }
});

/**
 * @swagger
 * /stats/activites/bottom:
 *   get:
 *     summary: Codes activité les moins représentés
 *     description: Retourne les codes d'activité avec le plus petit nombre d'entreprises
 *     tags: [Statistiques]
 *     parameters:
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 20
 *           maximum: 100
 *         description: Nombre de résultats
 *     responses:
 *       200:
 *         description: Codes activité les moins représentés
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ItemList'
 *       401:
 *         description: Non autorisé
 */
app.get('/stats/activites/bottom', verifyToken, async (req, res) => {
  let conn;
  try {
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);

    conn = await mysql.createConnection(dbConfig);

    const [rows] = await conn.query(`
      SELECT
        activite_principale_unite_legale as code,
        COUNT(siren) as count
      FROM unite_legale
      WHERE activite_principale_unite_legale IS NOT NULL
      GROUP BY activite_principale_unite_legale
      ORDER BY count ASC
      LIMIT ?
    `, [limit]);

    const items = rows.map(row => ({
      '@type': 'AggregateRating',
      '@id': `activity:${row.code}`,
      'identifier': row.code,
      'ratingCount': parseInt(row.count)
    }));

    const result = toJSONLD('ItemList', {
      numberOfItems: items.length,
      totalItems: items.length,
      itemListElement: items
    });

    res.json(result);
  } catch (error) {
    console.error('Error in /stats/activites/bottom:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: error.message
    });
  } finally {
    if (conn) await conn.end();
  }
});

// Démarrer le serveur
app.listen(PORT, '0.0.0.0', () => {
  console.log('========================================');
  console.log('API Spark démarrée (v1)');
  console.log(`Swagger UI: http://spark.siren.local/api-docs`);
  console.log(`Direct (dev): http://localhost:${PORT}/api-docs`);
  console.log(`Database: ${dbConfig.host}:${dbConfig.port}/${dbConfig.database}`);
  console.log('========================================');
});
