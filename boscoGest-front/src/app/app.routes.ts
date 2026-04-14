import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { permissionGuard } from './auth/permission.guard';
import { LoginComponent } from './login/login.component';
import { LayoutComponent } from './layout/layout.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { MyProfileComponent } from './my-profile/my-profile.component';
import { RolesListComponent } from './roles/roles-list/roles-list.component';
import { RoleFormComponent } from './roles/role-form/role-form.component';
import { RoleDetailComponent } from './roles/role-detail/role-detail.component';
import { EntitiesListComponent } from './entities/entities-list/entities-list.component';
import { EntityFormComponent } from './entities/entity-form/entity-form.component';
import { EntityDetailComponent } from './entities/entity-detail/entity-detail.component';
import { UsersListComponent } from './users/users-list/users-list.component';
import { UserFormComponent } from './users/user-form/user-form.component';
import { UserDetailComponent } from './users/user-detail/user-detail.component';
import { MembershipFormComponent } from './users/membership-form/membership-form.component';
import { UserImportComponent } from './users/user-import/user-import.component';
import { AssociateUserComponent } from './entities/associate-user/associate-user.component';
import { ActivitiesListComponent } from './activities/activities-list/activities-list.component';
import { ActivityDetailComponent } from './activities/activity-detail/activity-detail.component';
import { ActivityFormComponent } from './activities/activity-form/activity-form.component';
import { NewsListComponent } from './communications/communications-list/communications-list.component';
import { NewsFormComponent } from './communications/communications-form/communications-form.component';
import { NewsDetailComponent } from './communications/communications-detail/communications-detail.component';
import { NewsBlogComponent } from './communications/communications-blog/communications-blog.component';
import { MagazinesListComponent } from './magazines/magazines-list/magazines-list.component';
import { MagazineViewerComponent } from './magazines/magazine-viewer/magazine-viewer.component';
import { MagazineUploadComponent } from './magazines/magazine-upload/magazine-upload.component';
import { MagazineEditComponent } from './magazines/magazine-edit/magazine-edit.component';
import { ResourcesListComponent } from './resources/resources-list/resources-list.component';
import { ResourceFormComponent } from './resources/resource-form/resource-form.component';
import { ResourceDetailComponent } from './resources/resource-detail/resource-detail.component';
import { SettingsComponent } from './settings/settings.component';
import { NotificationsListComponent } from './notifications/notifications-list/notifications-list.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        component: DashboardComponent,
        data: { breadcrumb: 'Dashboard' }
      },
      {
        path: 'my-profile',
        component: MyProfileComponent,
        data: { breadcrumb: 'Mi Perfil' }
      },
      {
        path: 'roles',
        data: { breadcrumb: 'Roles' },
        children: [
          {
            path: '',
            component: RolesListComponent,
            canActivate: [permissionGuard('roles', 'manage')]
          },
          {
            path: 'new',
            component: RoleFormComponent,
            canActivate: [permissionGuard('roles', 'create')],
            data: { breadcrumb: 'Crear Rol' }
          },
          {
            path: ':id',
            component: RoleDetailComponent,
            canActivate: [permissionGuard('roles', 'manage')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            component: RoleFormComponent,
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
            component: EntitiesListComponent,
            canActivate: [permissionGuard('entities', 'manage')]
          },
          {
            path: 'new',
            component: EntityFormComponent,
            canActivate: [permissionGuard('entities', 'create')],
            data: { breadcrumb: 'Crear Asociación' }
          },
          {
            path: ':id',
            component: EntityDetailComponent,
            canActivate: [permissionGuard('entities', 'manage')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            component: EntityFormComponent,
            canActivate: [permissionGuard('entities', 'update')],
            data: { breadcrumb: 'Editar Asociación' }
          },
          {
            path: ':id/associate-user',
            component: AssociateUserComponent,
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
            component: UsersListComponent,
            canActivate: [permissionGuard('users', 'manage')]
          },
          {
            path: 'import',
            component: UserImportComponent,
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Importación Usuarios' }
          },
          {
            path: 'new',
            component: UserFormComponent,
            canActivate: [permissionGuard('users', 'create')],
            data: { breadcrumb: 'Crear Usuario' }
          },
          {
            path: ':id',
            component: UserDetailComponent,
            canActivate: [permissionGuard('users', 'manage')],
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            component: UserFormComponent,
            canActivate: [permissionGuard('users', 'update')],
            data: { breadcrumb: 'Editar Usuario' }
          },
          {
            path: ':id/create-membership',
            component: MembershipFormComponent,
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
            component: ActivitiesListComponent
          },
          {
            path: 'new',
            component: ActivityFormComponent,
            canActivate: [permissionGuard('activities', 'create')],
            data: { breadcrumb: 'Crear Actividad' }
          },
          {
            path: ':id',
            component: ActivityDetailComponent,
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            component: ActivityFormComponent,
            canActivate: [permissionGuard('activities', 'update')],
            data: { breadcrumb: 'Editar Actividad' }
          }
        ]
      },
      {
        path: 'blog',
        component: NewsBlogComponent,
        data: { breadcrumb: 'Blog' }
      },
      {
        path: 'communications',
        data: { breadcrumb: 'Comunicaciones' },
        children: [
          {
            path: '',
            component: NewsListComponent
          },
          {
            path: 'new',
            component: NewsFormComponent,
            canActivate: [permissionGuard('communications', 'create')],
            data: { breadcrumb: 'Crear Noticia' }
          },
          {
            path: ':id',
            component: NewsDetailComponent,
            data: { breadcrumb: 'Detalle' }
          },
          {
            path: ':id/edit',
            component: NewsFormComponent,
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
            component: MagazinesListComponent,
            canActivate: [permissionGuard('magazines', 'list')]
          },
          {
            path: 'upload',
            component: MagazineUploadComponent,
            canActivate: [permissionGuard('magazines', 'create')],
            data: { breadcrumb: 'Subir Revista' }
          },
          {
            path: ':id/edit',
            component: MagazineEditComponent,
            canActivate: [permissionGuard('magazines', 'update')],
            data: { breadcrumb: 'Editar Revista' }
          },
          {
            path: ':id',
            component: MagazineViewerComponent,
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
            component: ResourcesListComponent
          },
          {
            path: 'new',
            component: ResourceFormComponent,
            canActivate: [permissionGuard('resources', 'create')],
            data: { breadcrumb: 'Crear Recurso' }
          },
          {
            path: ':id/edit',
            component: ResourceFormComponent,
            canActivate: [permissionGuard('resources', 'update')],
            data: { breadcrumb: 'Editar Recurso' }
          },
          {
            path: ':id',
            component: ResourceDetailComponent,
            data: { breadcrumb: 'Ver Recurso' }
          }
        ]
      },
      {
        path: 'notifications',
        component: NotificationsListComponent,
        data: { breadcrumb: 'Notificaciones' }
      },
      {
        path: 'settings',
        component: SettingsComponent,
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
