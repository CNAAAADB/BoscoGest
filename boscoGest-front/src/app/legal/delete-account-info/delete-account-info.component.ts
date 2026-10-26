import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LEGAL } from '../legal-contact';

/**
 * Cómo eliminar la cuenta, en una página pública.
 *
 * Google Play pide dos cosas a las apps con registro: poder borrar la cuenta
 * desde dentro de la app (eso está en Mi perfil) y una URL donde cualquiera
 * pueda pedir ese borrado sin instalarla. Esta página es la segunda, y por eso
 * queda fuera del authGuard.
 */
@Component({
  selector: 'app-delete-account-info',
  imports: [RouterLink],
  templateUrl: './delete-account-info.component.html',
  styleUrl: '../legal.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DeleteAccountInfoComponent {
  legal = LEGAL;
}
