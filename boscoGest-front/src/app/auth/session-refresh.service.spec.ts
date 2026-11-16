import { fakeAsync, flushMicrotasks, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SessionRefreshService } from './session-refresh.service';
import { SessionCredentialService } from './session-credential.service';
import { environment } from '../../environments/environment';

describe('SessionRefreshService', () => {
  let service: SessionRefreshService;
  let requests: HttpTestingController;
  let store: jasmine.SpyObj<SessionCredentialService>;

  beforeEach(() => {
    localStorage.removeItem('authToken');
    store = jasmine.createSpyObj('SessionCredentialService', ['retrieve', 'persist', 'clear']);
    (store as any).native = false;
    store.retrieve.and.resolveTo(null);
    store.persist.and.resolveTo();
    store.clear.and.resolveTo();

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SessionCredentialService, useValue: store },
      ],
    });
    service = TestBed.inject(SessionRefreshService);
    requests = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    requests.verify();
    localStorage.removeItem('authToken');
  });

  it('uses the HttpOnly cookie and stores only the short-lived access token on web', fakeAsync(() => {
    let access: string | null | undefined;
    service.renew().subscribe((value) => access = value);
    flushMicrotasks();
    const req = requests.expectOne(`${environment.apiUrl}/auth/refresh`);
    expect(req.request.withCredentials).toBeTrue();
    expect(req.request.body).toEqual({});
    req.flush({ access_token: 'new-access', token_type: 'bearer' });
    flushMicrotasks();
    expect(access).toBe('new-access');
    expect(localStorage.getItem('authToken')).toBe('new-access');
    expect(store.persist).toHaveBeenCalledWith(undefined);
  }));

  it('deduplicates concurrent refresh requests', fakeAsync(() => {
    const values: (string | null)[] = [];
    service.renew().subscribe((token) => values.push(token));
    service.renew().subscribe((token) => values.push(token));
    flushMicrotasks();
    const requestsFound = requests.match(`${environment.apiUrl}/auth/refresh`);
    expect(requestsFound.length).toBe(1);
    requestsFound[0].flush({ access_token: 'shared', token_type: 'bearer' });
    flushMicrotasks();
    expect(values).toEqual(['shared', 'shared']);
  }));
});
