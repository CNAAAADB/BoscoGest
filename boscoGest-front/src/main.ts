import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

if (location.hostname === 'descargas.boscogest.com' && location.pathname === '/') {
  location.replace('/descargas/index.html');
} else {
  bootstrapApplication(App, appConfig).catch((err) => console.error(err));
}
