import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { EntitiesService } from './entities.service';
import { provideAppTesting } from '../testing/test-providers';
import { environment } from '../../environments/environment';

describe('Association selectors', () => {
  let service: EntitiesService;
  let http: HttpTestingController;

  const entities = [
    { id: 1, name: 'Superentidad', level: 1 },
    { id: 2, name: 'Confederación', level: 2 },
    { id: 3, name: 'Federación', level: 3 },
    { id: 4, name: 'Asociación A', level: 4 },
    { id: 5, name: 'Asociación B', level: 4 },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideAppTesting()] });
    service = TestBed.inject(EntitiesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('uses the association-only directory for general user search', () => {
    let received: number[] = [];
    service.getLocalAssociations().subscribe(items => received = items.map(item => item.id));
    const req = http.expectOne(`${environment.apiUrl}/entities/associations`);
    expect(req.request.method).toBe('GET');
    req.flush(entities.filter(item => item.level === 4));
    expect(received).toEqual([4, 5]);
  });

  it('excludes federation, confederation and superentity from accessible admin options', () => {
    let received: number[] = [];
    service.getAccessibleLocalAssociations().subscribe(items => received = items.map(item => item.id));
    const req = http.expectOne(`${environment.apiUrl}/entities/accessible`);
    expect(req.request.method).toBe('GET');
    req.flush(entities);
    expect(received).toEqual([4, 5]);
  });
});
