# Capacitor — Aplicaciones Nativas para BoscoGest

## Qué es Capacitor

Capacitor es un **runtime nativo** que envuelve la aplicación web Angular compilada dentro de un **WebView** nativo (WKWebView en iOS, WebView en Android). El resultado es una app nativa real (.apk/.ipa) que ejecuta la misma web app que se despliega en el navegador.

**No es un framework de UI** — la interfaz sigue siendo Angular Material. Capacitor solo proporciona:
- El contenedor nativo (WebView)
- Acceso a APIs nativas del dispositivo (filesystem, cámara, share, etc.)
- Empaquetado como app nativa para las tiendas

## Capacitor vs Ionic

| | Capacitor | Ionic |
|---|-----------|-------|
| **Tipo** | Runtime nativo | Librería de componentes UI |
| **Función** | Envolver web app en WebView + APIs nativas | Componentes con estilo móvil (tabs, cards, lists) |
| **¿Necesario para apps nativas?** | **Sí** | No |
| **¿Se usa en BoscoGest?** | **Sí** | **No** — usamos Angular Material |

## Arquitectura

```
┌─────────────────────────────────────┐
│         Código Angular único         │
│    (Angular Material + TypeScript)   │
└──────────────┬──────────────────────┘
               │ ng build
               ▼
┌─────────────────────────────────────┐
│     dist/boscoGest-front/browser/   │
│         (HTML/CSS/JS estáticos)      │
└──────────┬───────────┬──────────────┘
           │           │
     cap sync     Despliegue web
           │        (nginx, etc.)
           ▼
┌──────────────────┐  ┌──────────────┐
│  android/        │  │  ios/        │
│  (Android Studio)│  │  (Xcode)     │
│  WebView + assets│  │  WKWebView   │
└──────────────────┘  └──────────────┘
```

1. `ng build` compila Angular a ficheros estáticos
2. `npx cap sync` copia esos ficheros dentro de los proyectos nativos
3. Los proyectos nativos (`android/`, `ios/`) contienen un WebView que carga los assets

## Plugins instalados

| Plugin | Uso |
|--------|-----|
| `@capacitor/core` | Core del runtime, API `Capacitor.isNativePlatform()` |
| `@capacitor/cli` | CLI (`cap sync`, `cap add`, `cap run`) |
| `@capacitor/android` | Plataforma Android |
| `@capacitor/ios` | Plataforma iOS |
| `@capacitor/app` | Eventos de app (back button Android, estado de app) |
| `@capacitor/keyboard` | Control del teclado virtual (redimensionar body) |
| `@capacitor/status-bar` | Estilo y color de la barra de estado |
| `@capacitor/splash-screen` | Pantalla de carga al abrir la app |
| `@capacitor/filesystem` | Lectura/escritura de ficheros en el dispositivo |
| `@capacitor/browser` | Abrir URLs externas en navegador in-app |
| `@capacitor/share` | Share sheet nativo (compartir ficheros/URLs) |

## Configuración: `capacitor.config.ts`

```typescript
const config: CapacitorConfig = {
  appId: 'com.boscogest.app',
  appName: 'BoscoGest',
  webDir: 'dist/boscoGest-front/browser',
  plugins: {
    CapacitorHttp: { enabled: true },   // HTTP nativo → bypass CORS en móvil
    Keyboard: { resize: 'body' },       // Redimensiona body al abrir teclado
    SplashScreen: { backgroundColor: '#3D4E7C' }
  },
  server: {
    androidScheme: 'https'              // Origen del WebView en Android
  }
};
```

### CapacitorHttp

Cuando `CapacitorHttp.enabled: true`, Capacitor parchea `fetch()` y `XMLHttpRequest` en plataformas nativas para usar el stack HTTP nativo del dispositivo. Esto **elimina problemas de CORS** automáticamente en móvil sin tocar el backend. En web, no tiene efecto.

## Flujo de build

### Desarrollo con live reload

```bash
# Terminal 1: Servidor Angular
ng serve --host 0.0.0.0

# Terminal 2: App nativa con live reload
npx cap run android --livereload --external
npx cap run ios --livereload --external
```

La app nativa apunta al servidor de desarrollo → cambios en caliente.

### Producción

```bash
ng build --configuration production    # Build Angular
npx cap sync                           # Copiar assets a proyectos nativos
npx cap open android                   # Abrir en Android Studio → Build APK
npx cap open ios                       # Abrir en Xcode → Build IPA
```

## Comandos npm

| Comando | Descripción |
|---------|-------------|
| `npm run cap:sync` | Build Angular + sync a proyectos nativos |
| `npm run cap:android` | Abrir proyecto en Android Studio |
| `npm run cap:ios` | Abrir proyecto en Xcode |
| `npm run cap:run:android` | Build + ejecutar en emulador/dispositivo Android |
| `npm run cap:run:ios` | Build + ejecutar en simulador/dispositivo iOS |

## Entornos: Web vs Nativo

Para código condicional según la plataforma:

```typescript
import { Capacitor } from '@capacitor/core';

if (Capacitor.isNativePlatform()) {
  // Solo en Android/iOS
} else {
  // Solo en web
}
```

Esto se usa en:
- **Descargas de ficheros**: en web usa `<a download>`, en nativo usa Filesystem + Share
- **Back button**: solo en Android
- **Status bar**: solo en nativo

## Safe Areas (notch/gesture bar)

CSS usa `env(safe-area-inset-*)` para evitar que el contenido se solape con el notch o la gesture bar. En web estas variables resuelven a `0px` → sin impacto visual.

## Fuentes

Las fuentes (Roboto + Material Icons) están bundleadas localmente en `public/assets/fonts/` para que funcionen offline en apps nativas. No dependen de Google Fonts CDN.

## Cómo añadir nuevos plugins nativos

1. Instalar: `npm install @capacitor/nombre-plugin`
2. Importar y usar en el código Angular
3. Sincronizar: `npx cap sync`
4. Si requiere configuración nativa, editar `android/` o `ios/` según la documentación del plugin

## Estructura de directorios generada

```
boscoGest-front/
├── android/                 # Proyecto Android Studio (auto-generado)
│   ├── app/
│   │   └── src/main/assets/ # Web assets copiados por cap sync
│   └── ...
├── ios/                     # Proyecto Xcode (auto-generado)
│   ├── App/
│   │   └── App/public/      # Web assets copiados por cap sync
│   └── ...
├── capacitor.config.ts      # Configuración de Capacitor
├── src/                     # Código Angular (compartido web + nativo)
└── ...
```

## Qué NO incluye esta integración

- **Push notifications** — requiere Firebase (Android) + APNs (iOS), se puede añadir después
- **Soporte offline** — la app necesita conexión a la API
- **Iconos y splash screens personalizados** — usa los por defecto de Capacitor
