# Hightech cross
Simple code example that was challenged by FaceApp to me for their vacancy.
This service implements an API for a mobile app.
## Try it
Just start it:
```bash
docker-compose up -d
```
Go to [localhost:8081](http://localhost:8081/) for API documentation.

Go to [localhost:8080/admin](http://localhost:8080/admin/)
to create some entities.

Use [localhost:8080/api](http://localhost:8080/api/) endpoints.
## Endpoints
The service has many endpoints.
But the mobile app would mostly use those:
* `GET /api/crosses/current/` — current cross info + leaderboard.
* `GET /api/crosses/current/missions/` — mission stati for user (team).
* `PUT /api/crosses/current/missions/2/prompts/3/` —
take a prompt and get a time penalty.
* `POST /api/crosses/current/missions/5/answers/` —
guess the answer for mission.
## TODO list
* More docs.
* Tests.
