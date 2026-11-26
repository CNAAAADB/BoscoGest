import { TestBed } from '@angular/core/testing';
import { ActivityDetailComponent } from './activity-detail.component';
import { ActivityResponse } from '../../models/user.model';
import { provideAppTesting } from '../../testing/test-providers';

describe('ActivityDetailComponent authorization', () => {
  let component: ActivityDetailComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActivityDetailComponent],
      providers: [provideAppTesting()],
    }).compileComponents();
    component = TestBed.createComponent(ActivityDetailComponent).componentInstance;
  });

  it('allows a local admin to register for a confederal activity without admin actions', () => {
    component.activity.set({
      permissions: {
        can_edit: false, can_delete: false, can_manage_registrations: false,
        can_create_chat_group: false, can_register: true,
      },
    } as ActivityResponse);
    expect(component.canRegister()).toBeTrue();
    expect(component.showAdminActions()).toBeFalse();
    expect(component.canCreateChatGroup()).toBeFalse();
  });

  it('shows authorized actions only and denies missing permission data', () => {
    component.activity.set({} as ActivityResponse);
    expect(component.showAdminActions()).toBeFalse();
    expect(component.canRegister()).toBeFalse();
    component.activity.set({
      permissions: {
        can_edit: true, can_delete: false, can_manage_registrations: true,
        can_create_chat_group: true, can_register: false,
      },
    } as ActivityResponse);
    expect(component.canEditActivities()).toBeTrue();
    expect(component.canDeleteActivities()).toBeFalse();
    expect(component.canManageActivities()).toBeTrue();
    expect(component.canCreateChatGroup()).toBeTrue();
  });
});
