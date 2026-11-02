FROM node:24-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY src/service.mjs src/panel.html src/panel.js.txt src/panel.css.txt ./src/
COPY google/firestore-store.mjs google/http-server.mjs google/main.mjs ./google/
USER node
ENV NODE_ENV=production
CMD ["node", "google/main.mjs"]
