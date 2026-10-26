import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LEGAL } from '../legal-contact';

/**
 * Política de privacidad, pública y sin sesión.
 *
 * Google Play exige una URL de política de privacidad accesible sin instalar
 * la app y sin iniciar sesión, y la comprueba: por eso vive fuera del
 * authGuard y fuera del layout de la aplicación.
 */
@Component({
  selector: 'app-privacy-policy',
  imports: [RouterLink],
  templateUrl: './privacy-policy.component.html',
  styleUrl: '../legal.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PrivacyPolicyComponent {
  legal = LEGAL;
}
