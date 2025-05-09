docker build -t youtube-noti-app .
docker stop youtube-noti-container
docker rm youtube-noti-container
docker run --rm --name youtube-noti-container youtube-noti-app