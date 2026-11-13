// Dominio de tallas (debe coincidir con ALLOWED_SIZES del backend)
export type UserSize = 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL' | 'XXXL';

export const USER_SIZE_OPTIONS: UserSize[] = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL'];

/**
 * A user as returned by the API.
 *
 * Fields outside the public tier are nullable because the backend redacts them
 * according to the viewer's permissions (GDPR data minimisation): contact
 * fields need `users:read`, and dni/iban/address/birthdate need
 * `users:read_sensitive`. A redacted field arrives as null, so `null` means
 * either "not set" or "not visible to you" — do not treat it as empty data.
 */
export interface UserResponse {
  // Public tier — always present.
  id: number;
  name: string;
  surname: string;
  photo: string | null;
  job_position: string | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;

  // Contact tier — requires users:read.
  email: string | null;
  phone: string | null;
  size: UserSize | null;
  hobbies: string | null;

  // Sensitive tier — requires users:read_sensitive, or being the subject.
  dni: string | null;
  iban: string | null;
  address: string | null;
  birthdate: string | null;
}

/** A page of users, with the total so a paginator knows how many there are. */
export interface PaginatedUsers {
  items: UserResponse[];
  total: number;
  skip: number;
  limit: number;
}

/** A stored version of the GDPR data-processing clause. */
export interface ConsentClause {
  id: number;
  version: string;
  text: string;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
  created_by_id: number | null;
}

export interface ConsentClauseCreate {
  version: string;
  text: string;
  publish: boolean;
}

/** Status of the GDPR data-processing consent for the current user. */
export interface ConsentStatus {
  accepted: boolean;
  accepted_at: string | null;
  accepted_version: string | null;
  current_version: string;
  /** The clause itself, present only while it has not been accepted. */
  text: string | null;
}

/**
 * Creating a member on someone else's behalf.
 *
 * No password: one is generated server-side and never disclosed. The person
 * signs in through the one-shot link in their welcome email and chooses their
 * own there.
 */
export interface UserCreate {
  email: string | null;
  name: string;
  surname: string;
  phone: string | null;
  address?: string | null;
  birthdate: string;
  dni: string | null;
  photo?: string | null;
  iban?: string | null;
  size?: UserSize | null;
  hobbies?: string | null;
  job_position?: string | null;
  entity_id?: number | null;
  role_id?: number | null;
}

export interface UserUpdate {
  email?: string | null;
  name?: string | null;
  surname?: string | null;
  phone?: string | null;
  address?: string | null;
  birthdate?: string | null;
  dni?: string | null;
  photo?: string | null;
  iban?: string | null;
  size?: UserSize | null;
  hobbies?: string | null;
  job_position?: string | null;
  is_active?: boolean | null;
}

export interface UserDetails {
  id: number;
  email: string | null;
  name: string;
  surname: string;
  /** True until they choose a password of their own on first sign-in. */
  must_change_password: boolean;
  phone: string | null;
  address: string | null;
  birthdate: string;
  dni: string | null;
  photo: string | null;
  iban: string | null;
  size: UserSize | null;
  hobbies: string | null;
  job_position: string | null;
  is_active: boolean;
  created_at: string;
  groups: GroupResponse[];
  roles: RoleResponse[];
  memberships: MembershipDetails[];
}

export interface EntityResponse {
  id: number;
  name: string;
  level: number;
  parent_id: number | null;
  created_at: string;
  parent?: EntityResponse | null;
}

export interface EntityCreate {
  name: string;
  parent_id: number;
}

export interface EntityUpdate {
  name?: string | null;
}

export interface EntityDetails {
  id: number;
  name: string;
  level: number;
  parent_id: number | null;
  created_at: string;
  parent: EntityResponse | null;
  memberships: MembershipDetails[];
}

export interface RoleResponse {
  id: number;
  name: string;
  description: string | null;
  permissions?: PermissionResponse[];
}

export interface RoleCreate {
  name: string;
  description?: string | null;
  permission_ids?: number[];
}

export interface RoleUpdate {
  name?: string | null;
  description?: string | null;
  permission_ids?: number[];
}

export interface PermissionResponse {
  id: number;
  name: string;
  resource: string;
  action: string;
  description: string | null;
  conditions: any | null;
}

export interface PermissionCreate {
  name: string;
  resource: string;
  action: string;
  description?: string | null;
  conditions?: any | null;
}

export interface GroupResponse {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface MembershipResponse {
  id: number;
  user_id: number;
  role_id: number;
  entity_id: number;
  is_active: boolean;
  created_at: string;
}

export interface MembershipDetails {
  id: number;
  user_id: number;
  role_id: number;
  entity_id: number;
  is_active: boolean;
  created_at: string;
  user: UserResponse | null;
  role: RoleResponse | null;
  entity: EntityResponse | null;
}

export interface RoleDetails {
  id: number;
  name: string;
  description: string | null;
  permissions: PermissionResponse[];
  groups: GroupResponse[];
  memberships: MembershipResponse[];
}

// Activity Models
export interface ActivityResponse {
  id: number;
  title: string;
  description: string;
  image_url: string | null;
  date: string;
  /** Optional: activities created before it existed, or one-off ones, have none. */
  end_date?: string | null;
  capacity: number;
  price: number;
  allow_waitlist: boolean;
  entity_id: number;
  created_at: string;
  created_by_id: number;
  entity?: EntityResponse | null;
}

export interface ActivityCreate {
  title: string;
  description: string;
  image_url?: string | null;
  date: string;
  end_date?: string | null;
  capacity: number;
  price: number;
  allow_waitlist: boolean;
  entity_id: number;
}

export interface ActivityUpdate {
  title?: string | null;
  description?: string | null;
  image_url?: string | null;
  date?: string | null;
  end_date?: string | null;
  capacity?: number | null;
  price?: number | null;
  allow_waitlist?: boolean | null;
}

// Activity Registration Models
export interface ActivityRegistrationOut {
  id: number;
  status: 'pending' | 'accepted' | 'rejected' | 'waitlist';
  user_id: number;
  activity_id: number;
  registered_at: string;
}

export interface ActivityRegistrationWithUser extends ActivityRegistrationOut {
  user?: UserResponse;
}

// Communication Models
export type CommunicationStatus = 'draft' | 'review' | 'published' | 'archived';

export const COMMUNICATION_STATUS_LABELS: Record<CommunicationStatus, string> = {
  draft: 'Borrador',
  review: 'Revisión',
  published: 'Publicada',
  archived: 'Archivada',
};

export const COMMUNICATION_STATUS_COLORS: Record<CommunicationStatus, string> = {
  draft: '#9e9e9e',
  review: '#ff9800',
  published: '#4caf50',
  archived: '#607d8b',
};

export interface CommunicationResponse {
  id: number;
  title: string;
  content: string;
  image_url: string | null;
  entity_id: number;
  entity_name?: string;
  created_by_id: number;
  status: CommunicationStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface CommunicationCreate {
  title: string;
  content: string;
  image_url?: string | null;
  entity_id: number;
  status?: CommunicationStatus;
}

export interface StatusTransitionRequest {
  target_status: CommunicationStatus;
}

export interface CommunicationUpdate {
  title?: string | null;
  content?: string | null;
  image_url?: string | null;
}

export interface UserBasicInfo {
  id: number;
  name: string;
  surname: string;
  email: string;
}

export interface CommentResponse {
  id: number;
  content: string;
  communication_id: number;
  user_id: number;
  user: UserBasicInfo;
  created_at: string;
  updated_at: string;
}

export interface CommentCreate {
  content: string;
}

export interface CommentUpdate {
  content: string;
}

export interface CommunicationWithCommentsResponse extends CommunicationResponse {
  comments: CommentResponse[];
}

// Magazine Models
export interface MagazineResponse {
  id: number;
  title: string;
  collection: string | null;
  issue_number: number | null;
  description: string | null;
  file_path: string;
  entity_id: number;
  created_at: string;
}

export interface MagazineDetails extends MagazineResponse {
  entity: EntityResponse | null;
}

export interface MagazineCreate {
  title: string;
  collection?: string | null;
  issue_number?: number | null;
  description?: string | null;
  entity_id: number;
  file: File;
}

export interface MagazineUpdate {
  title?: string | null;
  collection?: string | null;
  issue_number?: number | null;
  description?: string | null;
}

// Entity Branding Models
export interface EntityBrandingResponse {
  id: number;
  entity_id: number;
  subdomain: string | null;
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  display_name: string | null;
  tagline: string | null;
  custom_footer: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntityBrandingCreate {
  entity_id: number;
  subdomain?: string | null;
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  display_name?: string | null;
  tagline?: string | null;
  custom_footer?: string | null;
}

export interface EntityBrandingUpdate {
  subdomain?: string | null;
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  display_name?: string | null;
  tagline?: string | null;
  custom_footer?: string | null;
}

export interface EntityBrandingWithEntity extends EntityBrandingResponse {
  entity: EntityResponse | null;
}

// Entity View Config Models
export interface EntityViewConfigResponse {
  id: number;
  entity_id: number;
  view_name: string;
  display_name: string;
  is_enabled: boolean;
  display_order: number;
  icon: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntityViewConfigUpdate {
  display_name?: string | null;
  is_enabled?: boolean | null;
  display_order?: number | null;
  icon?: string | null;
}

export interface ViewConfigItem {
  view_name: string;
  display_name: string;
  is_enabled: boolean;
  display_order: number;
  icon?: string | null;
}

export interface EntityViewConfigBulkUpdate {
  configs: ViewConfigItem[];
}

export interface EntityViewConfigListResponse {
  entity_id: number;
  configs: EntityViewConfigResponse[];
}

// Resource Models
export type ResourceType = 'link' | 'document' | 'image' | 'video';

export interface ResourceResponse {
  id: number;
  title: string;
  description: string | null;
  resource_type: ResourceType;
  url: string | null;
  file_path: string | null;
  original_filename: string | null;
  tags: string | null;
  entity_id: number;
  category_id: number | null;
  created_by: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ResourceCreatorBrief {
  id: number;
  name: string;
  surname: string;
}

export interface ResourceCategoryResponse {
  id: number;
  name: string;
  description: string | null;
  entity_id: number;
  is_active: boolean;
  created_at: string;
}

export interface ResourceDetails extends ResourceResponse {
  entity: EntityResponse | null;
  category: ResourceCategoryResponse | null;
  creator: ResourceCreatorBrief | null;
}

export interface ResourceCreateLink {
  title: string;
  description?: string | null;
  resource_type: 'link' | 'video';
  url: string;
  tags?: string | null;
  entity_id: number;
  category_id?: number | null;
}

export interface ResourceCreateFile {
  title: string;
  description?: string | null;
  resource_type: 'document' | 'image';
  tags?: string | null;
  entity_id: number;
  category_id?: number | null;
  file: File;
}

export interface ResourceUpdate {
  title?: string | null;
  description?: string | null;
  url?: string | null;
  tags?: string | null;
  category_id?: number | null;
}

export interface ResourceCategoryCreate {
  name: string;
  description?: string | null;
  entity_id: number;
}

export interface ResourceCategoryUpdate {
  name?: string | null;
  description?: string | null;
}

// Notification Models
export interface ActorBrief {
  id: number;
  name: string;
  surname: string;
}

export interface NotificationEntityBrief {
  id: number;
  name: string;
}

export interface NotificationResponse {
  id: number;
  recipient_id: number;
  actor_id: number | null;
  actor: ActorBrief | null;
  event_type: string;
  resource_type: string;
  resource_id: number | null;
  entity_id: number;
  entity: NotificationEntityBrief | null;
  title: string;
  body: string | null;
  data: Record<string, any> | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

export interface NotificationPreferenceResponse {
  event_type: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
}

export interface NotificationPreferencesUpdate {
  preferences: {
    event_type: string;
    in_app_enabled: boolean;
    email_enabled: boolean;
    push_enabled: boolean;
  }[];
}

// Membership Request Models
export type MembershipRequestStatus = 'pending' | 'accepted' | 'rejected';

export interface MembershipRequestResponse {
  id: number;
  user_id: number;
  entity_id: number;
  status: MembershipRequestStatus;
  message: string | null;
  rejection_reason: string | null;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  created_at: string;
  user: UserBasicInfo | null;
  entity: EntityResponse | null;
}

// Fee Models
export type FeeStatus =
  | 'pending'
  // The member has sent the receipt and it is waiting to be checked. Its own
  // state because with no payment gateway this is the only signal there is:
  // not money in the account yet, but no longer waiting on the member.
  | 'submitted'
  | 'paid'
  | 'overdue'
  | 'cancelled'
  // Covered on purpose and owing nothing — honorary members and the like.
  // Deliberately not the same as cancelled, which reads as billed by mistake.
  | 'exempt';

export const FEE_STATUS_LABELS: Record<FeeStatus, string> = {
  pending: 'Pendiente',
  submitted: 'Justificante enviado',
  paid: 'Pagada',
  overdue: 'Vencida',
  cancelled: 'Cancelada',
  exempt: 'Exenta',
};

export const FEE_STATUS_COLORS: Record<FeeStatus, string> = {
  pending: '#ff9800',
  submitted: '#1976d2',
  paid: '#2e7d32',
  overdue: '#c62828',
  cancelled: '#646c74',
  exempt: '#6a4c93',
};

// Periodicity = how often the fee is applied to a member (set per assignment)
export type FeePeriodicity =
  | 'weekly'
  | 'monthly'
  | 'quarterly'
  | 'four_monthly'
  | 'biannual'
  | 'annual';

export const FEE_PERIODICITY_LABELS: Record<FeePeriodicity, string> = {
  weekly: 'Semanal',
  monthly: 'Mensual',
  quarterly: 'Trimestral',
  four_monthly: 'Cuatrimestral',
  biannual: 'Semestral',
  annual: 'Anual',
};

export const FEE_PERIODICITY_OPTIONS: FeePeriodicity[] = [
  'weekly', 'monthly', 'quarterly', 'four_monthly', 'biannual', 'annual',
];

// A version of a fee's amount (history)
export interface FeeConfigResponse {
  id: number;
  fee_id: number;
  amount: number;
  valid_from: string;
  valid_until: string | null;
  created_by: number | null;
  created_at: string;
}

// A named fee belonging to an entity
export interface FeeResponse {
  id: number;
  entity_id: number;
  name: string;
  periodicity: FeePeriodicity;
  /** Month the yearly cycle starts on (1-12). 9 = the course, September to August. */
  period_start_month: number;
  auto_renew: boolean;
  reminder_days: number;
  is_active: boolean;
  created_at: string;
  current_config: FeeConfigResponse | null;
}

export interface FeeCreate {
  name: string;
  periodicity: FeePeriodicity;
  entity_ids: number[];
  amount: number;
  valid_from: string;
  valid_until?: string | null;
  auto_renew?: boolean;
  reminder_days?: number;
  period_start_month?: number;
}

/** A member's enrolment in a fee: who owes it, from when, and until when. */
export interface FeeSubscriptionResponse {
  id: number;
  fee_id: number;
  user_id: number;
  entity_id: number;
  starts_on: string;
  ends_on: string | null;
  exempt: boolean;
  exempt_reason: string | null;
  user_name: string | null;
  user_surname: string | null;
}

export interface FeeSubscribeRequest {
  user_ids: number[];
  starts_on?: string | null;
  exempt?: boolean;
  exempt_reason?: string | null;
}

export interface FeeMaintenanceRun {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: 'success' | 'error';
  trigger: 'scheduled' | 'manual';
  triggered_by_id: number | null;
  triggered_by: { id: number; name: string; surname: string } | null;
  overdue_count: number;
  reminded_count: number;
  renewed_count: number;
  details: { overdue?: number[]; reminded?: number[]; renewed?: any[] } | null;
  error: string | null;
}

export interface FeeVersionCreate {
  amount: number;
  valid_from: string;
  valid_until?: string | null;
}

export interface UserBrief {
  id: number;
  name: string;
  surname: string;
  email: string;
}

export interface MemberPreview {
  user_id: number;
  name: string;
  surname: string;
  role_name: string | null;
  already_assigned: boolean;
}

export interface FeeAssignmentResponse {
  id: number;
  fee_id: number;
  fee_name: string | null;
  user_id: number;
  entity_id: number;
  fee_config_id: number | null;
  periodicity: FeePeriodicity;
  period: string;
  amount: number;
  status: FeeStatus;
  due_date: string | null;
  paid_at: string | null;
  notes: string | null;

  /** Proof of payment. With no gateway, this is the whole payment record. */
  proof_reference: string | null;
  proof_submitted_at: string | null;
  /** Why the treasurer sent it back, so the member knows what to correct. */
  proof_rejected_reason: string | null;
  has_proof: boolean;
  created_at: string;
  user: UserBrief | null;
}

export interface FeeAssignmentGenerateRequest {
  fee_id: number;
  reference_date?: string | null;
  /** Omit to charge everyone enrolled, which is the normal case. Supplying ids
   *  narrows that roster; it cannot add somebody who is not enrolled. */
  user_ids?: number[] | null;
  due_date?: string | null;
}

export interface FeeAssignmentStatusUpdate {
  status: FeeStatus;
  notes?: string | null;
}

export interface FeeGenerateResult {
  created: number;
  skipped: number;
  /** Enrolled members recorded as owing nothing. */
  exempt: number;
  period: string;
  fee_id: number;
  entity_id: number;
}

export interface RegisterRequest {
  name: string;
  surname: string;
  email: string;
  password: string;
  phone: string | null;
  birthdate: string;
  dni: string | null;
  address?: string | null;
  entity_id: number;
  message?: string | null;
}

/**
 * What removing an association would affect, consulted before the deletion so
 * the interface can warn — or refuse — with the reason in hand.
 */
export interface EntityDeletionImpact {
  entity_id: number;
  entity_name: string;
  /** False when it has associations under it: those block the deletion. */
  can_delete: boolean;
  child_count: number;
  child_names: string[];
  /** Memberships that would be ended along with the association. */
  member_count: number;
}
