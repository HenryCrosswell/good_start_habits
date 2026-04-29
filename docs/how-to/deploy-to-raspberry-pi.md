# How to deploy to Raspberry Pi

This guide covers running the app on a Pi as a background service accessible from a browser on the same network. For a full kiosk (Pi drives its own screen automatically), see the [Raspberry Pi kiosk tutorial](../tutorials/raspberry-pi-kiosk.md).

---

## Prerequisites

- Raspberry Pi 3B+ or later
- Docker installed (`curl -fsSL https://get.docker.com | sh`)
- The project files on the Pi (via `scp`, `git clone`, or USB)

---

## 1. Prepare the project directory

```bash
cd ~/good_start_habits
cp .env.example .env
nano .env   # fill in SECRET_KEY and TrueLayer credentials
touch dashboard.db   # Docker bind-mount requires the file to exist
```

---

## 2. Start the container

```bash
docker compose up -d
```

The app will be available at `http://<pi-ip>:5000` from any device on the same network.

---

## 3. Make it start on boot

`docker-compose.yml` has `restart: unless-stopped`. This means the container restarts automatically after a reboot, as long as the Docker daemon itself starts on boot:

```bash
sudo systemctl enable docker
```

Verify after a reboot:

```bash
docker compose ps
```

---

## 4. Access from other devices

Find the Pi's IP:

```bash
hostname -I
```

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

---

## Updating the app

```bash
git pull
docker compose build
docker compose up -d
```

The database file is bind-mounted so your habit streaks and OAuth tokens survive the rebuild.

---

## Viewing logs

```bash
docker compose logs -f
```
