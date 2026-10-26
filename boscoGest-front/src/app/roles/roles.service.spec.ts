import { TestBed } from '@angular/core/testing';

import { RolesService } from './roles.service';
import { provideAppTesting } from '../testing/test-providers';

describe('RolesService', () => {
  let service: RolesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideAppTesting()],
    });
    service = TestBed.inject(RolesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
