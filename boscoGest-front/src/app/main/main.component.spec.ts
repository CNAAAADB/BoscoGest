import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MainComponent } from './main.component';
import { provideAppTesting } from '../testing/test-providers';

describe('MainComponent', () => {
  let component: MainComponent;
  let fixture: ComponentFixture<MainComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MainComponent],
      providers: [provideAppTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MainComponent);
    component = fixture.componentInstance;
    // Entradas obligatorias (input.required): sin darles valor el componente
    // revienta con NG0950 en el primer detectChanges, antes de cualquier
    // comprobación.
    fixture.componentRef.setInput('isLeftSidebarCollapsed', false);
    fixture.componentRef.setInput('screenWidth', 1280);
    fixture.componentRef.setInput('isMobileView', false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
