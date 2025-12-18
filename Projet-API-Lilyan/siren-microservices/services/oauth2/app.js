/**
 * Serveur OAuth2 simple avec Express
 */

const express = require('express');
const bodyParser = require('body-parser');
const OAuthServer = require('express-oauth-server');
const InMemoryModel = require('./model');
const swaggerUi = require('swagger-ui-express');
const swaggerSpec = require('./swagger');

const app = express();
const PORT = process.env.PORT || 3000;

// Créer une instance du modèle en mémoire
const model = new InMemoryModel();

// Initialiser le serveur OAuth2
app.oauth = new OAuthServer({
  model: model,
  accessTokenLifetime: 3600, // 1 heure
  refreshTokenLifetime: 86400, // 24 heures
  allowBearerTokensInQueryString: true
});

// Middleware pour parser le body
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));

// Logger les requêtes
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Router pour API v1
const v1Router = express.Router();

// Swagger UI (hors du versioning)
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
  customCss: '.swagger-ui .topbar { display: none }',
  customSiteTitle: 'OAuth2 API Documentation'
}));

// Route pour le JSON Swagger (hors du versioning)
app.get('/swagger.json', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.send(swaggerSpec);
});

/**
 * @swagger
 * /v1/health:
 *   get:
 *     summary: Vérifier la santé du serveur
 *     tags: [Health]
 *     responses:
 *       200:
 *         description: Le serveur fonctionne correctement
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Health'
 */
v1Router.get('/health', (req, res) => {
  res.json({
    '@context': [
      'https://schema.org/',
      {
        'hydra': 'http://www.w3.org/ns/hydra/core#'
      }
    ],
    '@type': 'HealthCheckResponse',
    status: 'OK',
    message: 'OAuth2 Server is running',
    version: 'v1',
    timestamp: new Date().toISOString()
  });
});

/**
 * @swagger
 * /v1/oauth/token:
 *   post:
 *     summary: Obtenir un token OAuth2
 *     tags: [OAuth2]
 *     description: |
 *       Génère un access token et un refresh token selon le grant type.
 *
 *       **Grant Types supportés:**
 *       - `password`: Authentification utilisateur (username + password)
 *       - `client_credentials`: Authentification machine-à-machine
 *       - `refresh_token`: Rafraîchir un access token expiré
 *     requestBody:
 *       required: true
 *       content:
 *         application/x-www-form-urlencoded:
 *           schema:
 *             oneOf:
 *               - type: object
 *                 title: Password Grant
 *                 required: [grant_type, username, password, client_id, client_secret]
 *                 properties:
 *                   grant_type:
 *                     type: string
 *                     enum: [password]
 *                   username:
 *                     type: string
 *                     example: user1
 *                   password:
 *                     type: string
 *                     example: password123
 *                   client_id:
 *                     type: string
 *                     example: client-app
 *                   client_secret:
 *                     type: string
 *                     example: secret123
 *               - type: object
 *                 title: Client Credentials Grant
 *                 required: [grant_type, client_id, client_secret]
 *                 properties:
 *                   grant_type:
 *                     type: string
 *                     enum: [client_credentials]
 *                   client_id:
 *                     type: string
 *                     example: client-app
 *                   client_secret:
 *                     type: string
 *                     example: secret123
 *               - type: object
 *                 title: Refresh Token Grant
 *                 required: [grant_type, refresh_token, client_id, client_secret]
 *                 properties:
 *                   grant_type:
 *                     type: string
 *                     enum: [refresh_token]
 *                   refresh_token:
 *                     type: string
 *                     description: Le refresh token obtenu précédemment
 *                   client_id:
 *                     type: string
 *                     example: client-app
 *                   client_secret:
 *                     type: string
 *                     example: secret123
 *     responses:
 *       200:
 *         description: Token généré avec succès
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/TokenResponse'
 *       400:
 *         description: Requête invalide
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       401:
 *         description: Credentials invalides
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
v1Router.post('/oauth/token', app.oauth.token());

/**
 * @swagger
 * /v1/secure:
 *   get:
 *     summary: Route protégée (exemple)
 *     tags: [OAuth2]
 *     description: Endpoint de test protégé par OAuth2. Nécessite un access token valide.
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Accès autorisé
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                   example: Accès sécurisé réussi!
 *                 user:
 *                   type: object
 *                   properties:
 *                     id:
 *                       type: string
 *                 token:
 *                   type: object
 *                   properties:
 *                     expiresAt:
 *                       type: string
 *                       format: date-time
 *       401:
 *         description: Token invalide ou manquant
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
v1Router.get('/secure', app.oauth.authenticate(), (req, res) => {
  res.json({
    message: 'Accès sécurisé réussi!',
    user: res.locals.oauth.token.user,
    token: {
      expiresAt: res.locals.oauth.token.accessTokenExpiresAt
    }
  });
});

/**
 * @swagger
 * /v1/me:
 *   get:
 *     summary: Obtenir les informations de l'utilisateur connecté
 *     tags: [Users]
 *     description: Retourne les informations de l'utilisateur associé au token
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Informations utilisateur
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/User'
 *       401:
 *         description: Non authentifié
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       404:
 *         description: Utilisateur non trouvé
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 error:
 *                   type: string
 *                   example: User not found
 */
v1Router.get('/me', app.oauth.authenticate(), (req, res) => {
  const userId = res.locals.oauth.token.user.id;
  const user = model.users.find(u => u.id === userId);

  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }

  res.json({
    id: user.id,
    username: user.username
  });
});

/**
 * @swagger
 * /v1/users:
 *   get:
 *     summary: Lister tous les utilisateurs
 *     tags: [Users]
 *     description: Retourne la liste de tous les utilisateurs (sans mots de passe)
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Liste des utilisateurs
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/UserList'
 *       401:
 *         description: Non authentifié
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
v1Router.get('/users', app.oauth.authenticate(), (req, res) => {
  const users = model.users.map(u => ({
    id: u.id,
    username: u.username
  }));

  res.json({ users });
});

/**
 * @swagger
 * /v1/debug/dump:
 *   get:
 *     summary: Afficher le contenu du store en mémoire
 *     tags: [Debug]
 *     description: |
 *       Retourne le contenu complet du store en mémoire (clients, users, tokens).
 *       **ATTENTION:** À utiliser uniquement en développement !
 *     responses:
 *       200:
 *         description: Contenu du store
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 clients:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       clientId:
 *                         type: string
 *                       grants:
 *                         type: array
 *                         items:
 *                           type: string
 *                       redirectUris:
 *                         type: array
 *                         items:
 *                           type: string
 *                 users:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/User'
 *                 tokens:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       accessToken:
 *                         type: string
 *                         description: Aperçu du token (tronqué)
 *                       refreshToken:
 *                         type: string
 *                         description: Aperçu du refresh token (tronqué)
 *                       clientId:
 *                         type: string
 *                       userId:
 *                         type: string
 *                       accessTokenExpiresAt:
 *                         type: string
 *                         format: date-time
 *                       refreshTokenExpiresAt:
 *                         type: string
 *                         format: date-time
 */
v1Router.get('/debug/dump', (req, res) => {
  res.json({
    clients: model.clients.map(c => ({
      clientId: c.clientId,
      grants: c.grants,
      redirectUris: c.redirectUris
    })),
    users: model.users.map(u => ({
      id: u.id,
      username: u.username
    })),
    tokens: model.tokens.map(t => ({
      accessToken: t.accessToken.substring(0, 20) + '...',
      refreshToken: t.refreshToken ? t.refreshToken.substring(0, 20) + '...' : null,
      clientId: t.clientId,
      userId: t.userId,
      accessTokenExpiresAt: t.accessTokenExpiresAt,
      refreshTokenExpiresAt: t.refreshTokenExpiresAt
    }))
  });
});

// Monter le router v1
app.use('/v1', v1Router);

/**
 * Gestion des erreurs 404
 */
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.method} ${req.path} not found`
  });
});

/**
 * Gestion globale des erreurs
 */
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: err.name || 'Internal Server Error',
    message: err.message
  });
});

/**
 * Démarrer le serveur
 */
app.listen(PORT, () => {
  console.log('========================================');
  console.log(`OAuth2 Server démarré sur le port ${PORT}`);
  console.log('========================================');
  console.log('\nDocumentation:');
  console.log(`  Swagger UI:   http://oauth.siren.local/api-docs`);
  console.log(`  OpenAPI JSON: http://oauth.siren.local/swagger.json`);
  console.log(`  Direct (dev): http://localhost:${PORT}/api-docs`);
  console.log('\nEndpoints disponibles (API v1):');
  console.log('  GET  /v1/health          - Santé du serveur');
  console.log('  POST /v1/oauth/token     - Obtenir un token');
  console.log('  GET  /v1/secure          - Route protégée (exemple)');
  console.log('  GET  /v1/me              - Informations utilisateur connecté');
  console.log('  GET  /v1/users           - Liste des utilisateurs');
  console.log('  GET  /v1/debug/dump      - Debug du store en mémoire');
  console.log('\nCredentials configurés (.env):');
  console.log('  Client ID:     client-app');
  console.log('  Client Secret: Dev_Client_Secret_2024!');
  console.log('  Username:      user1 / user2');
  console.log('  Password:      Voir .env.example');
  console.log('========================================\n');

  // Afficher le dump initial
  model.dump();
});

module.exports = app;
