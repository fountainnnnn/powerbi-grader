FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Install http-server to serve the app
RUN npm install -g http-server

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

# Expose port
EXPOSE 3000

# Serve the app
CMD ["http-server", "dist", "-p", "3000", "-c-1"]
