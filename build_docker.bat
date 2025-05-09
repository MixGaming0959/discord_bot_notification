docker build -t youtube-noti-app .
docker stop youtube-noti-container
docker rm youtube-noti-container
docker run --name youtube-noti-container --restart always youtube-noti-app
