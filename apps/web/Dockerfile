FROM node:20-slim
WORKDIR /code
RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install
COPY . .
CMD ["pnpm", "dev"]
