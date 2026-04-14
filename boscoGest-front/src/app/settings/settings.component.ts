import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';

import { BrandingService } from './branding.service';
import { ViewConfigService } from './view-config.service';
import { AuthService } from '../auth/auth.service';
import { EntitiesService } from '../entities/entities.service';
import { NotificationPreferencesComponent } from '../notifications/notification-preferences/notification-preferences.component';
import {
  EntityBrandingResponse,
  EntityBrandingUpdate,
  EntityViewConfigResponse,
  ViewConfigItem,
  EntityResponse
} from '../models/user.model';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatTabsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSelectModule,
    DragDropModule,
    NotificationPreferencesComponent
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.css'
})
export class SettingsComponent implements OnInit {
  // Estado de carga
  loading = signal(true);
  savingBranding = signal(false);
  savingViews = signal(false);

  // Entidades donde el usuario es admin
  adminEntities = signal<EntityResponse[]>([]);
  selectedEntityId = signal<number | null>(null);

  // Branding
  brandingForm!: FormGroup;
  currentBranding = signal<EntityBrandingResponse | null>(null);
  logoPreview = signal<string | null>(null);
  selectedLogoFile = signal<File | null>(null);

  // View configs
  viewConfigs = signal<EntityViewConfigResponse[]>([]);

  // Para preview de colores
  colorPreview = computed(() => ({
    primary: this.brandingForm?.get('primary_color')?.value || '#1976d2',
    secondary: this.brandingForm?.get('secondary_color')?.value || '#424242',
    accent: this.brandingForm?.get('accent_color')?.value || '#ff4081'
  }));

  constructor(
    private fb: FormBuilder,
    private brandingService: BrandingService,
    private viewConfigService: ViewConfigService,
    private authService: AuthService,
    private entitiesService: EntitiesService,
    private snackBar: MatSnackBar
  ) {
    this.initBrandingForm();
  }

  ngOnInit(): void {
    this.loadAdminEntities();
  }

  private initBrandingForm(): void {
    this.brandingForm = this.fb.group({
      subdomain: ['', [Validators.pattern(/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/)]],
      display_name: ['', [Validators.maxLength(100)]],
      tagline: ['', [Validators.maxLength(200)]],
      primary_color: ['#1976d2', [Validators.pattern(/^#[0-9A-Fa-f]{6}$/)]],
      secondary_color: ['#424242', [Validators.pattern(/^#[0-9A-Fa-f]{6}$/)]],
      accent_color: ['#ff4081', [Validators.pattern(/^#[0-9A-Fa-f]{6}$/)]],
      custom_footer: ['']
    });
  }

  private loadAdminEntities(): void {
    this.entitiesService.getAdminEntities().subscribe({
      next: (entities) => {
        this.adminEntities.set(entities);
        if (entities.length > 0) {
          this.selectEntity(entities[0].id);
        } else {
          this.loading.set(false);
        }
      },
      error: (error) => {
        console.error('Error loading admin entities:', error);
        this.loading.set(false);
        this.showSnackBar('Error al cargar las asociaciones', 'error');
      }
    });
  }

  selectEntity(entityId: number): void {
    this.selectedEntityId.set(entityId);
    this.loading.set(true);

    // Cargar branding y view configs en paralelo
    this.loadBranding(entityId);
    this.loadViewConfigs(entityId);
  }

  private loadBranding(entityId: number): void {
    this.brandingService.getEntityBranding(entityId).subscribe({
      next: (branding) => {
        this.currentBranding.set(branding);
        this.patchBrandingForm(branding);
        if (branding.logo_url) {
          this.logoPreview.set(branding.logo_url);
        }
      },
      error: (error) => {
        if (error.status === 404) {
          // No branding configured, use defaults
          this.currentBranding.set(null);
          this.brandingForm.reset({
            primary_color: '#1976d2',
            secondary_color: '#424242',
            accent_color: '#ff4081'
          });
          this.logoPreview.set(null);
        } else {
          console.error('Error loading branding:', error);
        }
        this.loading.set(false);
      },
      complete: () => this.loading.set(false)
    });
  }

  private loadViewConfigs(entityId: number): void {
    this.viewConfigService.getEntityViewConfigs(entityId).subscribe({
      next: (response) => {
        this.viewConfigs.set(response.configs.sort((a, b) => a.display_order - b.display_order));
      },
      error: (error) => {
        console.error('Error loading view configs:', error);
      }
    });
  }

  private patchBrandingForm(branding: EntityBrandingResponse): void {
    this.brandingForm.patchValue({
      subdomain: branding.subdomain || '',
      display_name: branding.display_name || '',
      tagline: branding.tagline || '',
      primary_color: branding.primary_color,
      secondary_color: branding.secondary_color,
      accent_color: branding.accent_color,
      custom_footer: branding.custom_footer || ''
    });
  }

  // Branding methods
  onLogoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];

      // Validar tipo de archivo
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'];
      if (!allowedTypes.includes(file.type)) {
        this.showSnackBar('Tipo de archivo no permitido. Use PNG, JPG o SVG.', 'error');
        return;
      }

      // Validar tamaño (5MB max)
      if (file.size > 5 * 1024 * 1024) {
        this.showSnackBar('El archivo es demasiado grande. Máximo 5MB.', 'error');
        return;
      }

      this.selectedLogoFile.set(file);

      // Preview
      const reader = new FileReader();
      reader.onload = (e) => {
        this.logoPreview.set(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  }

  removeLogo(): void {
    this.selectedLogoFile.set(null);
    this.logoPreview.set(null);
  }

  saveBranding(): void {
    if (!this.brandingForm.valid || !this.selectedEntityId()) {
      return;
    }

    this.savingBranding.set(true);
    const entityId = this.selectedEntityId()!;
    const formData: EntityBrandingUpdate = this.brandingForm.value;

    // Si hay un logo seleccionado, subirlo primero
    if (this.selectedLogoFile()) {
      this.brandingService.uploadLogo(entityId, this.selectedLogoFile()!).subscribe({
        next: () => {
          this.selectedLogoFile.set(null);
          this.updateOrCreateBranding(entityId, formData);
        },
        error: (error) => {
          console.error('Error uploading logo:', error);
          this.savingBranding.set(false);
          this.showSnackBar('Error al subir el logo', 'error');
        }
      });
    } else {
      this.updateOrCreateBranding(entityId, formData);
    }
  }

  private updateOrCreateBranding(entityId: number, formData: EntityBrandingUpdate): void {
    const operation = this.currentBranding()
      ? this.brandingService.updateBranding(entityId, formData)
      : this.brandingService.createBranding({ entity_id: entityId, ...formData });

    operation.subscribe({
      next: (branding) => {
        this.currentBranding.set(branding);
        this.savingBranding.set(false);
        this.showSnackBar('Branding guardado correctamente', 'success');

        // Aplicar branding al DOM
        this.brandingService.applyBrandingToDOM(branding);
      },
      error: (error) => {
        console.error('Error saving branding:', error);
        this.savingBranding.set(false);
        this.showSnackBar(error.error?.detail || 'Error al guardar el branding', 'error');
      }
    });
  }

  resetBrandingToDefault(): void {
    this.brandingForm.reset({
      primary_color: '#1976d2',
      secondary_color: '#424242',
      accent_color: '#ff4081'
    });
    this.brandingService.resetBrandingToDefault();
  }

  // View config methods
  toggleView(config: EntityViewConfigResponse): void {
    const entityId = this.selectedEntityId();
    if (!entityId) return;

    this.viewConfigService.updateViewConfig(entityId, config.view_name, {
      is_enabled: !config.is_enabled
    }).subscribe({
      next: (updated) => {
        const configs = this.viewConfigs();
        const index = configs.findIndex(c => c.id === updated.id);
        if (index !== -1) {
          configs[index] = updated;
          this.viewConfigs.set([...configs]);
        }
      },
      error: (error) => {
        console.error('Error updating view config:', error);
        this.showSnackBar('Error al actualizar la vista', 'error');
      }
    });
  }

  updateViewName(config: EntityViewConfigResponse, newName: string): void {
    const entityId = this.selectedEntityId();
    if (!entityId || !newName.trim()) return;

    this.viewConfigService.updateViewConfig(entityId, config.view_name, {
      display_name: newName.trim()
    }).subscribe({
      next: (updated) => {
        const configs = this.viewConfigs();
        const index = configs.findIndex(c => c.id === updated.id);
        if (index !== -1) {
          configs[index] = updated;
          this.viewConfigs.set([...configs]);
        }
      },
      error: (error) => {
        console.error('Error updating view name:', error);
        this.showSnackBar('Error al actualizar el nombre', 'error');
      }
    });
  }

  onViewDrop(event: CdkDragDrop<EntityViewConfigResponse[]>): void {
    const configs = [...this.viewConfigs()];
    moveItemInArray(configs, event.previousIndex, event.currentIndex);

    // Actualizar display_order
    const updatedConfigs: ViewConfigItem[] = configs.map((config, index) => ({
      view_name: config.view_name,
      display_name: config.display_name,
      is_enabled: config.is_enabled,
      display_order: index + 1,
      icon: config.icon
    }));

    this.viewConfigs.set(configs.map((c, i) => ({ ...c, display_order: i + 1 })));
    this.saveViewOrder(updatedConfigs);
  }

  private saveViewOrder(configs: ViewConfigItem[]): void {
    const entityId = this.selectedEntityId();
    if (!entityId) return;

    this.savingViews.set(true);
    this.viewConfigService.bulkUpdateViewConfigs(entityId, { configs }).subscribe({
      next: (response) => {
        this.viewConfigs.set(response.configs.sort((a, b) => a.display_order - b.display_order));
        this.savingViews.set(false);
        this.showSnackBar('Orden guardado', 'success');
      },
      error: (error) => {
        console.error('Error saving view order:', error);
        this.savingViews.set(false);
        this.showSnackBar('Error al guardar el orden', 'error');
      }
    });
  }

  resetViewConfigs(): void {
    const entityId = this.selectedEntityId();
    if (!entityId) return;

    this.viewConfigService.resetViewConfigs(entityId).subscribe({
      next: (response) => {
        this.viewConfigs.set(response.configs.sort((a, b) => a.display_order - b.display_order));
        this.showSnackBar('Vistas restauradas a valores por defecto', 'success');
      },
      error: (error) => {
        console.error('Error resetting view configs:', error);
        this.showSnackBar('Error al restaurar las vistas', 'error');
      }
    });
  }

  private showSnackBar(message: string, type: 'success' | 'error'): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 3000,
      panelClass: type === 'error' ? ['error-snackbar'] : ['success-snackbar']
    });
  }

  getEntityName(entityId: number): string {
    return this.adminEntities().find(e => e.id === entityId)?.name || '';
  }
}
