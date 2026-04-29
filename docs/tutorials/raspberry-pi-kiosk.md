# Tutorial: Raspberry Pi kiosk

By the end of this tutorial you will have the dashboard running on a Raspberry Pi, launching automatically on boot and displaying full-screen in Chromium.

This tutorial assumes:
- A Raspberry Pi 3B+ or later with Raspberry Pi OS (64-bit recommended)
- The Pi is connected to a display
- You have SSH access or a keyboard/mouse

---

## 1. Install Docker on the Pi

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in so the group change takes effect.

---

## 2. Copy the project to the Pi

From your development machine:

```bash
scp -r . pi@<pi-ip>:~/good_start_habits
```

Or clone directly on the Pi:

```bash
git clone <repo-url> ~/good_start_habits
cd ~/good_start_habits
```

---

## 3. Create your `.env` file on the Pi

```bash
cd ~/good_start_habits
cp .env.example .env
nano .env
```

Fill in at minimum:

```
SECRET_KEY=<a long random string>
```

If you want the budget page, also fill in the TrueLayer credentials (see [Connect a bank account](../how-to/connect-a-bank.md)).

---

## 4. Create the database file

Docker bind-mounts require the file to already exist:

```bash
touch dashboard.db
```

---

## 5. Start the container

```bash
docker compose up -d
```

Check it is running:

```bash
docker compose ps
docker compose logs
```

Open `http://localhost:5000` in a browser on the Pi to confirm.

---

## 6. Set Docker to start on boot

Docker Compose's `restart: unless-stopped` already handles this, provided the Docker daemon itself starts on boot. Verify:

```bash
sudo systemctl enable docker
sudo systemctl status docker
```

---

## 7. Install Chromium and set up kiosk mode

On Raspberry Pi OS, Chromium is usually pre-installed. If not:

```bash
sudo apt install chromium-browser
```

Create an autostart entry:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/dashboard.desktop
```

Paste:

```
[Desktop Entry]
Type=Application
Name=Dashboard
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --app=http://localhost:5000
```

---

## 8. Disable screen blanking

The Pi's display manager will blank the screen after a few minutes by default. Add to `/etc/xdg/lxsession/LXDE-pi/autostart`:

```
@xset s off
@xset -dpms
@xset s noblank
```

---

## 9. Reboot and verify

```bash
sudo reboot
```

After reboot, Chromium should open automatically in kiosk mode pointing at the dashboard. The Docker container will have started automatically before the display manager loads.

---

## Troubleshooting

**Container not starting after reboot** — check `docker compose logs`. Common cause: `.env` is missing or `SECRET_KEY` is blank.

**Chromium shows a connection error** — the container may still be starting. Add a small delay to the autostart entry: `Exec=bash -c "sleep 10 && chromium-browser ..."`.

**Screen is blank** — check the xset autostart lines are in the right file for your desktop environment.
