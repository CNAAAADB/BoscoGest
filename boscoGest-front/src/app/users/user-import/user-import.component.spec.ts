import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserImportComponent } from './user-import.component';
import { provideAppTesting } from '../../testing/test-providers';

describe('UserImportComponent', () => {
  let component: UserImportComponent;
  let fixture: ComponentFixture<UserImportComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserImportComponent],
      providers: [provideAppTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserImportComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
