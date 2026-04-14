import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'es.urjc.boscogest',
  appName: 'BoscoGest',
  webDir: 'dist/boscoGest-front/browser',
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
    Keyboard: {
      resize: 'body',
    },
    SplashScreen: {
      backgroundColor: '#3D4E7C',
    },
  },
  server: {
    androidScheme: 'https',
  },
};

export default config;
