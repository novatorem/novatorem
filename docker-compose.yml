version: '3.8'
services:
    spotify-readme:
        env_file:
            - .env
        build: .
        ports:
            - "5000:5000"
        volumes:
            - ./api:/api
volumes:
  persistent:
