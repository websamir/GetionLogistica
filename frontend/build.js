const fs  = require('fs');
const path = require('path');

const API_BASE_URL = process.env.API_BASE_URL || 'https://getionlogistica.onrender.com';
const src  = path.join(__dirname, 'index.html');
const dist = path.join(__dirname, 'dist', 'index.html');

fs.mkdirSync(path.join(__dirname, 'dist'), { recursive: true });

let html = fs.readFileSync(src, 'utf8');

const injection = `<script>var __API_BASE_URL__ = "${API_BASE_URL}";</script>`;
html = html.replace('</head>', injection + '\n</head>');

fs.writeFileSync(dist, html, 'utf8');
console.log(`Build OK — API_BASE_URL: ${API_BASE_URL}`);
console.log(`Output: ${dist}`);
