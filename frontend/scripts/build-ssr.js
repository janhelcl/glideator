'use strict';

process.env.BABEL_ENV = 'production';
process.env.NODE_ENV = 'production';

const path = require('path');
const webpack = require('webpack');

const frontendRoot = path.resolve(__dirname, '..');
const sourceRoot = path.join(frontendRoot, 'src');
const outputPath = path.join(frontendRoot, 'server-build');

const config = {
  name: 'glideator-ssr',
  mode: 'production',
  target: 'node18',
  entry: path.join(sourceRoot, 'entry-server.jsx'),
  devtool: false,
  output: {
    path: outputPath,
    filename: 'entry-server.cjs',
    chunkFilename: 'chunks/[name].[contenthash:8].cjs',
    library: { type: 'commonjs2' },
    chunkLoading: 'require',
    clean: true,
  },
  resolve: {
    extensions: ['.js', '.jsx', '.json'],
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        include: sourceRoot,
        use: {
          loader: require.resolve('babel-loader'),
          options: {
            babelrc: false,
            configFile: false,
            cacheDirectory: true,
            cacheCompression: false,
            presets: [require.resolve('babel-preset-react-app')],
          },
        },
      },
      {
        test: /\.css$/,
        use: path.join(__dirname, 'ssr-empty-loader.js'),
      },
      {
        test: /\.(png|jpe?g|gif|webp|ico|svg|woff2?|eot|ttf|otf)$/i,
        type: 'asset/resource',
      },
    ],
  },
  optimization: {
    minimize: false,
    splitChunks: false,
    runtimeChunk: false,
  },
  performance: {
    hints: false,
  },
  stats: 'errors-warnings',
};

webpack(config, (error, stats) => {
  if (error) {
    console.error(error.stack || error);
    process.exitCode = 1;
    return;
  }

  if (stats.hasErrors()) {
    console.error(stats.toString({ all: false, errors: true, warnings: true }));
    process.exitCode = 1;
    return;
  }

  if (stats.hasWarnings()) {
    console.warn(stats.toString({ all: false, warnings: true }));
  }

  console.log(`SSR bundle written to ${outputPath}`);
});
