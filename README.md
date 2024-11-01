# TE_EPUB Localimage

To know how to download **The Economist** Magzine every week, please ref to [README](./README.tc.md).

## 1. Environment setup

```bash
git clone repo
virtualenv .venv
source .venv/bin/activate
pip
```

## 2. check if a .epub file has missing images

```bash
python trawl.py check '/Users/apple/Calibre Library/calibre/The Economist [Oct 25, 2024] (11)/The Economist [Oct 25, 2024] - calibre.epub'
```

```
2 HTTP images found. Check log for details.
```

If you want to know which file has missing images, use `-l` option:

```bash
python trawl.py check -l '/Users/apple/Calibre Library/calibre/The Economist [Oct 25, 2024] (11)/The Economist [Oct 25, 2024] - calibre.epub'
```

## 3. Fill up the missing images

```bash
python trawl.py replenish '/Users/apple/Calibre Library/calibre/The Economist [Oct 25, 2024] (11)/The Economist [Oct 25, 2024] - calibre.epub'
```
This will create a new .epub file with a timestamp, right next to the original file, in this case *The Economist [Oct 25, 2024] (11)/The Economist [Oct 25, 2024] - calibre.**20241102_034502**.epub*.

🚨 If you want to directly override the original file, use `-r` option:

```bash
python trawl.py replenish -r '/Users/apple/Calibre Library/calibre/The Economist [Oct 25, 2024] (11)/The Economist [Oct 25, 2024] - calibre.epub'
```
