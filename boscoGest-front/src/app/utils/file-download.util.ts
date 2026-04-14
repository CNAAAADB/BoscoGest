import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

/**
 * Cross-platform file download.
 * - Web: uses <a download> + blob URL
 * - Native (iOS/Android): writes to cache via Filesystem, then opens share sheet
 */
export async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  if (Capacitor.isNativePlatform()) {
    const arrayBuffer = await blob.arrayBuffer();
    const base64 = arrayBufferToBase64(arrayBuffer);

    const result = await Filesystem.writeFile({
      path: filename,
      data: base64,
      directory: Directory.Cache,
    });

    await Share.share({
      title: filename,
      url: result.uri,
    });
  } else {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => window.URL.revokeObjectURL(url), 100);
  }
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
