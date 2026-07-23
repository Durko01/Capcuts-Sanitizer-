#!/data/data/com.termux/files/usr/bin/bash
#
# capcuts — launcher untuk CapCuts Video Sanitizer
# Menjalankan server.py di background lalu auto-buka browser ke UI upload.
#
# Ketik "capcuts" di Termux (setelah alias di-setup lewat install.sh)
# buat langsung menjalankan script ini.

set -euo pipefail

APP_DIR="$HOME/capcuts_app"
PORT=8787
URL="http://127.0.0.1:${PORT}"
PIDFILE="$APP_DIR/.capcuts.pid"

cd "$APP_DIR" 2>/dev/null || {
  echo "❌ Folder capcuts_app gak ketemu di $APP_DIR"
  echo "   Jalankan install.sh dulu, atau sesuaikan APP_DIR di script ini."
  exit 1
}

# Kalau server lama masih hidup, matiin dulu biar port gak bentrok
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "♻️  Server lama (PID $OLD_PID) masih jalan, di-restart..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

echo "🚀 Menjalankan CapCuts server..."
python server.py &
SERVER_PID=$!
echo "$SERVER_PID" > "$PIDFILE"

# Tunggu server siap nerima koneksi (max 10 detik)
for i in $(seq 1 20); do
  if curl -s -o /dev/null "$URL"; then
    break
  fi
  sleep 0.5
done

# Auto buka browser default
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$URL"
else
  echo "👉 Buka manual di browser: $URL"
fi

# Notifikasi Termux kalau termux-api kepasang
if command -v termux-notification >/dev/null 2>&1; then
  termux-notification --title "CapCuts" --content "Server aktif di $URL" >/dev/null 2>&1 || true
fi

echo ""
echo "✅ Server jalan (PID $SERVER_PID) di $URL"
echo "   Tekan Ctrl+C buat stop."
wait "$SERVER_PID"
