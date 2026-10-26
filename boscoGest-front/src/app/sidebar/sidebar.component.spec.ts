import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SidebarComponent } from './sidebar.component';
import { provideAppTesting } from '../testing/test-providers';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],
      providers: [provideAppTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    // Entradas obligatorias (input.required): sin darles valor el componente
    // revienta con NG0950 en el primer detectChanges, antes de cualquier
    // comprobación.
    fixture.componentRef.setInput('isLeftSidebarCollapsed', false);
    fixture.componentRef.setInput('isMobileView', false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
