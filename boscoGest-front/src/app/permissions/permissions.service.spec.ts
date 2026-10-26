import { TestBed } from '@angular/core/testing';

import { PermissionsService } from './permissions.service';
import { provideAppTesting } from '../testing/test-providers';

describe('PermissionsService', () => {
  let service: PermissionsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideAppTesting()],
    });
    service = TestBed.inject(PermissionsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
