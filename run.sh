docker rm -f elitebot
docker build -t elitebot .
docker run -d --name elitebot -v data:/app/data --restart unless-stopped elitebot
