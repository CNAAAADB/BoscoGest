import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { permissionGuard } from './auth/permission.guard';
import { LoginComponent } from './login/login.component';
import { LayoutComponent } from './layout/layout.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'register', loadComponent: () => import('./auth/register/register.component').then(m => m.RegisterComponent) },
  // Where the one-shot link in a welcome email lands. Outside the auth guard:
  // the whole point is that whoever follows it has no session yet.
  { path: 'activar', loadComponent: () => import('./auth/activate/activate.component').then(m => m.ActivateComponent) },
  // Forgotten password: asking for the link, and where the link lands. Outside
  // the guard for the same reason.
  { path: 'recuperar', loadComponent: () => import('./auth/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent) },
  { path: 'restablecer', loadComponent: () => import('./auth/reset-password/reset-password.component').then(m => m.ResetPasswordComponent) },
  // Páginas legales públicas. Fuera del authGuard a propósito: Google Play
  // comprueba la política de privacidad y la página de eliminación de cuenta
  // sin instalar la app ni iniciar sesión, y una redirección al login es
  // motivo de rechazo de la ficha.
  {
    path: 'privacidad',
    loadComponent: () => import('./legal/privacy-policy/privacy-policy.component').then(m => m.PrivacyPolicyComponent),
  },
  {
    path: 'eliminar-cuenta',
    loadComponent: () => import('./legal/delete-account-info/delete-account-info.component').then(m => m.DeleteAccountInfoComponent),
  },
  {
    path: 'pending',
    loadComponent: () => import('./auth/pending-approval/pending-approval.component').then(m => m.PendingApprovalComponent),
    canActivate: [authGuard],
  },
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
        data: { breadcrumb: 'Dashboard' }
      },
      {
        path: 'my-profile',
        loadComponent: () => import('./my-profile/my-profile.component').then(m => m.MyProfileComponent),
        data: { breadcrumb: 'Mi Perfil' }
      },
      {
        path: 'membership-requests',
        loadComponent: () => import('./membership-requests/membership-requests-list/membership-requests-list.component').then(m => m.MembershipRequestsListComponent),
        canActivate: [permissionGuard('memberships', 'review')],
        data: { breadcrumb: 'Solicitudes de alta' }
      },
      {
        path: 'roles',
        data: { breadcrumb: 'Roles' },
        children: [
          {
            path: '',
            loadComponent: () => import('./roles/roles-list/roles-list.component').then(m => m.RolesListComponent),
            canActivate: [permissionGuard('roles', 'manage')]
          },
          {
            path: 'new',
            loadComponent: () => import('./roles/role-form/role-form.component').then(m => m.RoleFormComponent),
            canActivate: [permissionGuard('roles', 'create')],
            data: { breadcrumb: 'Crear Rol' }
          },
          {
            path: ':id',
            loadComponent: () => import('./roles/role-detail/role-detail.component').then(m => m.RoleDetailComponent),
            canActivate: [permissionGuard('roles', 'manage')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./roles/role-form/role-form.component').then(m => m.RoleFormComponent),
            canActivate: [permissionGuard('roles', 'update')],
            data: { breadcrumb: 'Editar Rol' }
          }
        ]
      },
      {
        path: 'entities',
        data: { breadcrumb: 'Asociaciones' },
        children: [
          {
            path: '',
            loadComponent: () => import('./entities/entities-list/entities-list.component').then(m => m.EntitiesListComponent),
            canActivate: [permissionGuard('entities', 'update')]
          },
          {
            path: 'new',
            loadComponent: () => import('./entities/entity-form/entity-form.component').then(m => m.EntityFormComponent),
            canActivate: [permissionGuard('entities', 'create')],
            data: { breadcrumb: 'Crear Asociación' }
          },
          {
            path: ':id',
            loadComponent: () => import('./entities/entity-detail/entity-detail.component').then(m => m.EntityDetailComponent),
            canActivate: [permissionGuard('entities', 'update')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./entities/entity-form/entity-form.component').then(m => m.EntityFormComponent),
            canActivate: [permissionGuard('entities', 'update')],
            data: { breadcrumb: 'Editar Asociación' }
          },
          {
            path: ':id/associate-user',
            loadComponent: () => import('./entities/associate-user/associate-user.component').then(m => m.AssociateUserComponent),
            canActivate: [permissionGuard('memberships', 'manage')],
            data: { breadcrumb: 'Asociar Usuario' }
          }
        ]
      },
      {
        path: 'users',
        data: { breadcrumb: 'Usuarios' },
        children: [
          {
            path: '',
            loadComponent: () => import('./users/users-list/users-list.component').then(m => m.UsersListComponent),
            canActivate: [permissionGuard('users', 'manage')]
          },
          {
            path: 'import',
            loadComponent: () => import('./users/user-import/user-import.component').then(m => m.UserImportComponent),
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Importación Usuarios' }
          },
          {
            path: 'import/history',
            loadComponent: () => import('./users/bulk-upload-history/bulk-upload-history.component').then(m => m.BulkUploadHistoryComponent),
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Historial Importaciones' }
          },
          {
            // El detalle era un modal. Como vista tiene dirección propia, se
            // puede recargar, compartir y volver a ella, que es lo que pide una
            // tabla de cientos de filas.
            path: 'import/history/:id',
            loadComponent: () => import('./users/bulk-upload-history/job-detail/job-detail.component').then(m => m.JobDetailComponent),
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Detalle de importación' }
          },
          {
            path: 'new',
            loadComponent: () => import('./users/user-form/user-form.component').then(m => m.UserFormComponent),
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Crear Usuario' }
          },
          {
            path: ':id',
            loadComponent: () => import('./users/user-detail/user-detail.component').then(m => m.UserDetailComponent),
            canActivate: [permissionGuard('users', 'manage')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./users/user-form/user-form.component').then(m => m.UserFormComponent),
            canActivate: [permissionGuard('users', 'update')],
            data: { breadcrumb: 'Editar Usuario' }
          },
          {
            path: ':id/create-membership',
            loadComponent: () => import('./users/membership-form/membership-form.component').then(m => m.MembershipFormComponent),
            canActivate: [permissionGuard('memberships', 'manage')],
            data: { breadcrumb: 'Crear Membresía' }
          }
        ]
      },
      {
        path: 'activities',
        data: { breadcrumb: 'Actividades' },
        children: [
          {
            path: '',
            loadComponent: () => import('./activities/activities-list/activities-list.component').then(m => m.ActivitiesListComponent)
          },
          {
            path: 'new',
            loadComponent: () => import('./activities/activity-form/activity-form.component').then(m => m.ActivityFormComponent),
            canActivate: [permissionGuard('activities', 'create')],
            data: { breadcrumb: 'Crear Actividad' }
          },
          {
            path: ':id',
            loadComponent: () => import('./activities/activity-detail/activity-detail.component').then(m => m.ActivityDetailComponent),
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./activities/activity-form/activity-form.component').then(m => m.ActivityFormComponent),
            canActivate: [permissionGuard('activities', 'update')],
            data: { breadcrumb: 'Editar Actividad' }
          }
        ]
      },
      {
        path: 'blog',
        loadComponent: () => import('./communications/communications-blog/communications-blog.component').then(m => m.NewsBlogComponent),
        data: { breadcrumb: 'Blog' }
      },
      {
        path: 'communications',
        data: { breadcrumb: 'Comunicaciones' },
        children: [
          {
            path: '',
            loadComponent: () => import('./communications/communications-list/communications-list.component').then(m => m.NewsListComponent)
          },
          {
            path: 'new',
            loadComponent: () => import('./communications/communications-form/communications-form.component').then(m => m.NewsFormComponent),
            canActivate: [permissionGuard('communications', 'create')],
            data: { breadcrumb: 'Crear Noticia' }
          },
          {
            path: ':id',
            loadComponent: () => import('./communications/communications-detail/communications-detail.component').then(m => m.NewsDetailComponent),
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./communications/communications-form/communications-form.component').then(m => m.NewsFormComponent),
            canActivate: [permissionGuard('communications', 'edit')],
            data: { breadcrumb: 'Editar Noticia' }
          }
        ]
      },
      {
        path: 'magazines',
        data: { breadcrumb: 'Revistas' },
        children: [
          {
            path: '',
            loadComponent: () => import('./magazines/magazines-list/magazines-list.component').then(m => m.MagazinesListComponent),
            canActivate: [permissionGuard('magazines', 'list')]
          },
          {
            path: 'upload',
            loadComponent: () => import('./magazines/magazine-upload/magazine-upload.component').then(m => m.MagazineUploadComponent),
            canActivate: [permissionGuard('magazines', 'create')],
            data: { breadcrumb: 'Subir Revista' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./magazines/magazine-edit/magazine-edit.component').then(m => m.MagazineEditComponent),
            canActivate: [permissionGuard('magazines', 'update')],
            data: { breadcrumb: 'Editar Revista' }
          },
          {
            path: ':id',
            loadComponent: () => import('./magazines/magazine-viewer/magazine-viewer.component').then(m => m.MagazineViewerComponent),
            canActivate: [permissionGuard('magazines', 'read')],
            data: { breadcrumb: 'Ver Revista' }
          }
        ]
      },
      {
        path: 'resources',
        data: { breadcrumb: 'Recursos' },
        children: [
          {
            path: '',
            loadComponent: () => import('./resources/resources-list/resources-list.component').then(m => m.ResourcesListComponent)
          },
          {
            path: 'new',
            loadComponent: () => import('./resources/resource-form/resource-form.component').then(m => m.ResourceFormComponent),
            canActivate: [permissionGuard('resources', 'create')],
            data: { breadcrumb: 'Crear Recurso' }
          },
          {
            path: ':id/edit',
            loadComponent: () => import('./resources/resource-form/resource-form.component').then(m => m.ResourceFormComponent),
            canActivate: [permissionGuard('resources', 'update')],
            data: { breadcrumb: 'Editar Recurso' }
          },
          {
            path: ':id',
            loadComponent: () => import('./resources/resource-detail/resource-detail.component').then(m => m.ResourceDetailComponent),
            data: { breadcrumb: 'Ver Recurso' }
          }
        ]
      },
      {
        path: 'fees',
        canActivate: [permissionGuard('fees', 'manage')],
        loadComponent: () => import('./fees/fee-admin/fee-admin.component').then(m => m.FeeAdminComponent),
        data: { breadcrumb: 'Cuotas' }
      },
      {
        path: 'fees/mine',
        loadComponent: () => import('./fees/my-fees/my-fees.component').then(m => m.MyFeesComponent),
        data: { breadcrumb: 'Mis Cuotas' }
      },
      {
        path: 'fees/maintenance',
        canActivate: [permissionGuard('fees', 'maintenance', 'root')],
        loadComponent: () => import('./fees/fee-maintenance/fee-maintenance.component').then(m => m.FeeMaintenanceComponent),
        data: { breadcrumb: 'Mantenimiento de cuotas' }
      },
      {
        path: 'notifications',
        loadComponent: () => import('./notifications/notifications-list/notifications-list.component').then(m => m.NotificationsListComponent),
        data: { breadcrumb: 'Notificaciones' }
      },
      {
        path: 'chat',
        loadComponent: () => import('./chat/chat.component').then(m => m.ChatComponent),
        data: { breadcrumb: 'Chat' }
      },
      {
        path: 'settings',
        loadComponent: () => import('./settings/settings.component').then(m => m.SettingsComponent),
        canActivate: [permissionGuard('branding', 'update')],
        data: { breadcrumb: 'Configuración' }
      },
      {
        path: 'download-app',
        loadComponent: () => import('./download-app/download-app.component').then(m => m.DownloadAppComponent),
        data: { breadcrumb: 'Descargar App' }
      },
      { path: '', redirectTo: '/dashboard', pathMatch: 'full' }
    ]
  },
  { path: '**', redirectTo: '' }
];
