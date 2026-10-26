import { Component, OnInit, signal, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MembershipRequestService } from '../../membership-requests/membership-request.service';
import { NativePickerDirective } from '../../shared/native-picker.directive';

interface EntityOption {
  id: number;
  name: string;
  level: number;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    NativePickerDirective,
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RegisterComponent implements OnInit {
  private router = inject(Router);
  private requestService = inject(MembershipRequestService);

  // Step control
  currentStep = signal(0);

  // Personal data
  name = signal('');
  surname = signal('');
  email = signal('');
  password = signal('');
  confirmPassword = signal('');
  phone = signal('');
  birthdate = signal('');
  /** Upper bound for the birthdate, as the native date input wants it (YYYY-MM-DD, local). */
  readonly today = new Date().toLocaleDateString('sv-SE');
  dni = signal('');
  address = signal('');

  // Entity selection
  entities = signal<EntityOption[]>([]);
  selectedEntityId = signal<number | null>(null);
  message = signal('');
  loadingEntities = signal(false);

  // Submission
  submitting = signal(false);
  errorMessage = signal('');
  successRequest = signal<{ entity_name: string } | null>(null);

  ngOnInit(): void {
    this.loadingEntities.set(true);
    this.requestService.getPublicEntities().subscribe({
      next: (entities) => {
        this.entities.set(entities);
        this.loadingEntities.set(false);
      },
      error: () => this.loadingEntities.set(false),
    });
  }

  // ── Step navigation ──────────────────────────────────────────────────

  nextStep(): void {
    this.errorMessage.set('');
    if (this.currentStep() === 0 && !this.validatePersonalData()) return;
    if (this.currentStep() === 1 && !this.validateEntityStep()) return;
    this.currentStep.update((s) => s + 1);
  }

  prevStep(): void {
    this.errorMessage.set('');
    this.currentStep.update((s) => s - 1);
  }

  // ── Validation ───────────────────────────────────────────────────────

  validatePersonalData(): boolean {
    if (!this.name().trim() || !this.surname().trim()) {
      this.errorMessage.set('Nombre y apellidos son obligatorios');
      return false;
    }
    if (!this.email().trim() || !this.email().includes('@')) {
      this.errorMessage.set('Introduce un email válido');
      return false;
    }
    if (this.password().length < 8) {
      this.errorMessage.set('La contraseña debe tener al menos 8 caracteres');
      return false;
    }
    if (!/\d/.test(this.password())) {
      this.errorMessage.set('La contraseña debe contener al menos un número');
      return false;
    }
    if (!/[A-Z]/.test(this.password())) {
      this.errorMessage.set('La contraseña debe contener al menos una mayúscula');
      return false;
    }
    if (this.password() !== this.confirmPassword()) {
      this.errorMessage.set('Las contraseñas no coinciden');
      return false;
    }
    if (!this.phone().trim()) {
      this.errorMessage.set('El teléfono es obligatorio');
      return false;
    }
    if (!this.birthdate()) {
      this.errorMessage.set('La fecha de nacimiento es obligatoria');
      return false;
    }
    if (!this.dni().trim()) {
      this.errorMessage.set('El DNI es obligatorio');
      return false;
    }
    return true;
  }

  validateEntityStep(): boolean {
    if (!this.selectedEntityId()) {
      this.errorMessage.set('Debes seleccionar una entidad');
      return false;
    }
    return true;
  }

  // ── Submit ───────────────────────────────────────────────────────────

  submit(): void {
    this.errorMessage.set('');
    this.submitting.set(true);

    const selectedEntity = this.entities().find(
      (e) => e.id === this.selectedEntityId()
    );

    this.requestService
      .register({
        name: this.name().trim(),
        surname: this.surname().trim(),
        email: this.email().trim(),
        password: this.password(),
        phone: this.phone().trim(),
        birthdate: this.birthdate(),
        dni: this.dni().trim(),
        address: this.address().trim() || null,
        entity_id: this.selectedEntityId()!,
        message: this.message().trim() || null,
      })
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.successRequest.set({
            entity_name: selectedEntity?.name ?? 'la entidad',
          });
          this.currentStep.set(2); // success step
        },
        error: (err) => {
          this.submitting.set(false);
          const detail = err?.error?.detail;
          if (err?.status === 409) {
            // Email, DNI or phone already taken: all three are on the first
            // step, so take the person back to where they can change it.
            this.errorMessage.set(detail ?? 'Ya existe una cuenta con esos datos');
            this.currentStep.set(0);
          } else {
            this.errorMessage.set(detail ?? 'Error al enviar la solicitud');
          }
        },
      });
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}
