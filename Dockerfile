FROM node:10
WORKDIR /usr/src/app
COPY server/package*.json ./
RUN npm install
COPY . .

EXPOSE 3000
CMD [ "node", "server" ]
