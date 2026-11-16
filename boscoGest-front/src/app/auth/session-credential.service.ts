import { Injectable, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { NativeBiometric } from '@capgo/capacitor-native-biometric';

/**
 * Only rotating refresh credentials survive app restarts.
 * Native: iOS Keychain / Android Keystore, never localStorage.
 * Browser: HttpOnly/Secure cookie set by the API; JS never receives it from storage.
 */
@Injectable({ providedIn: 'root' })
export class SessionCredentialService {
  readonly native = Capacitor.isNativePlatform();
  private readonly vault = 'api.boscogest.com:refresh';
  private readonly biometricSetting = 'boscogest.useBiometrics';
  readonly biometricEnabled = signal(localStorage.getItem(this.biometricSetting) === 'yes');
  private unlocked = false;

  async persist(token: string | null | undefined): Promise<void> {
    if (!this.native || !token) return;
    // Never store a password; this is an individually revocable refresh secret.
    await NativeBiometric.setCredentials({
      username: 'BoscoGest',
      password: token,
      server: this.vault,
    });
  }

  async retrieve(): Promise<string | null> {
    if (!this.native) return null;
    try {
      const result = await NativeBiometric.getCredentials({ server: this.vault });
      return result.password || null;
    } catch {
      return null;
    }
  }

  /** Once per app launch, not on every HTTP call or token rotation. */
  async unlock(): Promise<boolean> {
    if (!this.native || this.unlocked) return true;
    if (!this.biometricEnabled()) {
      this.unlocked = true;
      return true;
    }
    try {
      const available = await NativeBiometric.isAvailable();
      if (!available.isAvailable) return false;
      await NativeBiometric.verifyIdentity({
        title: 'Acceder a BoscoGest',
        reason: 'Confirma tu identidad para abrir BoscoGest',
        negativeButtonText: 'Cancelar',
      });
      this.unlocked = true;
      return true;
    } catch {
      // Cancelling biometrics does not destroy the saved session:
      // the person can retry or use their password.
      return false;
    }
  }

  async enableBiometrics(enable: boolean): Promise<boolean> {
    if (!this.native) return false;
    if (enable) {
      try {
        const availability = await NativeBiometric.isAvailable();
        if (!availability.isAvailable) return false;
        await NativeBiometric.verifyIdentity({
          title: 'Activar el acceso biométrico',
          reason: 'Confirma que quieres utilizar huella o reconocimiento facial',
        });
      } catch {
        return false;
      }
    }
    localStorage.setItem(this.biometricSetting, enable ? 'yes' : 'no');
    this.biometricEnabled.set(enable);
    this.unlocked = true;
    return true;
  }

  async clear(): Promise<void> {
    this.unlocked = false;
    if (!this.native) return;
    try {
      await NativeBiometric.deleteCredentials({ server: this.vault });
    } catch {
      // The server revokes the credential as part of logout.
    }
  }
}
