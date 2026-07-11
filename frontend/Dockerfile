# Frontend image — npm install happens ONCE here, at build time, while
# internet is available. The running container never needs network access
# beyond talking to the backend container over the Docker network.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# --host is required so the Vite dev server is reachable from outside the
# container (otherwise it only binds to localhost inside the container).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
