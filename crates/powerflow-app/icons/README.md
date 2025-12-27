# App Icons

需要準備以下圖標檔案：

- `icon.png` - Tray icon (建議 32x32 或 64x64)
- `32x32.png` - App icon 32x32
- `128x128.png` - App icon 128x128
- `128x128@2x.png` - App icon 128x128 @2x (256x256)
- `icon.icns` - macOS app icon
- `icon.ico` - Windows app icon

## 建議設計

- 使用閃電 ⚡ 或電池圖示
- 深色背景適配，使用淺色圖示
- 簡潔明瞭，適合小尺寸顯示

## 暫時解決方案

在開發階段，Tauri 會使用預設圖標。
你可以稍後使用 `tauri icon` 命令從單一 PNG 檔案生成所有所需的圖標：

```bash
cargo tauri icon path/to/your-icon.png
```
