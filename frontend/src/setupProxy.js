const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Proxy llms.txt endpoints to backend
  app.use(
    '/llms.txt',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  app.use(
    '/llms/sites',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  // Proxy API requests to backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  // Proxy MCP requests to backend
  app.use(
    '/mcp',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};

