#!/data/data/com.termux/files/usr/bin/bash
#
# install.sh — setup CapCuts di Termux dari nol
# Jalankan sekali: bash install.sh

set -e

echo "📦 Update package list..."
pkg update -y

echo "📦 Install dependencies (python, ffmpeg, termux-api, git)..."
pkg install -y python ffmpeg termux-api git

echo "📦 Install Python packages..."
pip install --upgrade pip
pip install flask

APP_DIR="$HOME/capcuts_app"
SCRIPT_PATH="$APP_DIR/capcuts.sh"

chmod +x "$SCRIPT_PATH" 2>/dev/null || true

# Tambahin alias "capcuts" biar tinggal ketik capcuts langsung jalan
SHELL_RC="$HOME/.bashrc"
[ -n "${ZSH_VERSION:-}" ] && SHELL_RC="$HOME/.zshrc"

ALIAS_LINE="alias capcuts='bash $SCRIPT_PATH'"

if ! grep -qF "$ALIAS_LINE" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# CapCuts launcher" >> "$SHELL_RC"
  echo "$ALIAS_LINE" >> "$SHELL_RC"
  echo "✅ Alias 'capcuts' ditambahin ke $SHELL_RC"
else
  echo "ℹ️  Alias 'capcuts' udah ada di $SHELL_RC"
fi

echo ""
echo "🎉 Install selesai!"
echo "   Jalankan: source $SHELL_RC"
echo "   Lalu tinggal ketik: capcuts"
