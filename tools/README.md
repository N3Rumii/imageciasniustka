# Tools

## img_viewer.py — Infinite Image Viewer

A standalone Python/Tkinter desktop image viewer with virtual infinite scrolling.
Originally designed for offline image browsing, it can be used as a companion to
szurubooru for quickly reviewing downloaded pool collections.

### Features

- **Infinite scroll** — virtual rendering that only loads images visible on screen
- **Thumbnail grid** — browse a folder as a grid of thumbnails
- **Full-screen reader** — click any thumbnail to enter the reader
- **Keyboard navigation** — arrow keys scroll, snap-to-grid to jump between images
- **Fit to screen** — toggle between fit-width and fit-height modes
- **Multi-format** — supports JPG, PNG, WebP, BMP, GIF

### Usage

```bash
pip install pillow
python tools/img_viewer.py
```

1. Click the folder icon to select a directory of images
2. Browse thumbnails in the grid
3. Click a thumbnail to open the infinite-scroll reader
4. Use ↑↓ or scroll to navigate; use ←→ when snap-to-grid is enabled

### Tips for szurubooru Users

If you've downloaded pool images from your szurubooru instance, point the viewer
at the download folder to preview them in the infinite-scroll reader. For AVIF
files, ensure `pillow-avif-plugin` is installed:

```bash
pip install pillow-avif-plugin
```
