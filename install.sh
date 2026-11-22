#!/usr/bin/env sh
# Install Gallery Zero color themes into macOS Terminal.app without Gatekeeper quarantine.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/BigCactusLabs/gallery-zero/main/install.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/BigCactusLabs/gallery-zero/main/install.sh | sh -s -- rothko demuth
#   ./install.sh --list
set -eu

REPO="BigCactusLabs/gallery-zero"
REF="${GALLERY_ZERO_REF:-main}"

usage() {
  cat <<'EOF'
Gallery Zero — install macOS Terminal color themes

Usage:
  install.sh [OPTIONS] [COLLECTION...]

Examples:
  install.sh                      Install all 56 themes (all 8 collections)
  install.sh rothko demuth        Install only the Rothko and Demuth collections
  install.sh "De Amaral" monet    Names are case- and space-insensitive
  install.sh --dry-run rothko     Preview what would be installed
  install.sh --list               List available collections

Options:
  -c, --collection, --pack NAME   Install only the named collection(s) (repeatable or comma-separated)
  -l, --list                      List available collections and exit
      --dry-run                   Show what would be installed without touching Terminal.app
      --prune                     Also remove retired Gallery Zero profiles from selected collections
  -h, --help                      Show this help
EOF
}

find_python3() {
  for candidate in \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3
  do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1; then
    py="$(command -v python3)"
    # On macOS, /usr/bin/python3 is a shim that prompts for Xcode CLT unless CLT is installed.
    if [ "$py" != "/usr/bin/python3" ] || [ "$(uname -s)" != "Darwin" ] || xcode-select -p >/dev/null 2>&1; then
      printf '%s\n' "$py"
      return 0
    fi
  fi
  return 1
}

# Parse options and convert bare collection names into --collection flags.
list_only=0
n=$#
i=0
while [ "$i" -lt "$n" ]; do
  arg=$1
  shift
  i=$((i + 1))
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    -l|--list)
      list_only=1
      set -- "$@" --list
      ;;
    --dry-run|--prune)
      set -- "$@" "$arg"
      ;;
    -c|--collection|--pack)
      if [ "$i" -ge "$n" ]; then
        printf 'error: %s requires a collection name\n' "$arg" >&2
        exit 2
      fi
      val=$1
      shift
      i=$((i + 1))
      set -- "$@" --collection "$val"
      ;;
    --collection=*|--pack=*)
      set -- "$@" --collection "${arg#*=}"
      ;;
    -*)
      printf 'error: unknown option: %s (try --help)\n' "$arg" >&2
      exit 2
      ;;
    *)
      set -- "$@" --collection "$arg"
      ;;
  esac
done

if [ "$list_only" -eq 0 ] && [ "$(uname -s)" != "Darwin" ]; then
  printf 'error: Gallery Zero profiles are for macOS Terminal.app\n' >&2
  exit 2
fi

if ! PYTHON="$(find_python3)"; then
  printf 'error: python3 is required to run the installer.\n' >&2
  printf 'Install Xcode Command Line Tools (xcode-select --install), or download a zip from\n' >&2
  printf 'https://bigcactuslabs.github.io/gallery-zero/ and drag .terminal files into\n' >&2
  printf 'Terminal -> Settings -> Profiles.\n' >&2
  exit 2
fi

# Use the local checkout when invoked directly from a cloned repo; otherwise fetch a fresh tarball.
src=""
if [ -f "$0" ]; then
  script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
  if [ -f "$script_dir/tools/profiles.py" ] && [ -d "$script_dir/themes" ]; then
    src="$script_dir"
  fi
fi

tmp=""
cleanup() {
  if [ -n "$tmp" ] && [ -d "$tmp" ]; then
    rm -rf "$tmp"
  fi
}
trap cleanup EXIT INT TERM

if [ -z "$src" ]; then
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/gallery-zero.XXXXXX")"
  tarball_url="${GALLERY_ZERO_TARBALL:-https://github.com/${REPO}/archive/refs/heads/${REF}.tar.gz}"
  printf 'Downloading Gallery Zero...\n' >&2
  curl -fsSL "$tarball_url" | tar -xz -C "$tmp"
  for dir in "$tmp"/*; do
    if [ -f "$dir/tools/profiles.py" ] && [ -d "$dir/themes" ]; then
      src="$dir"
      break
    fi
  done
  if [ -z "$src" ]; then
    printf 'error: downloaded archive did not contain Gallery Zero\n' >&2
    exit 1
  fi
fi

"$PYTHON" "$src/tools/profiles.py" install-terminal "$@"
