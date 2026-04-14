export interface UserResponse {
  id: number;
  email: string;
  name: string;
  surname: string;
  phone: string;
  address: string | null;
  birthdate: string;
  dni: string;
  photo: string | null;
  iban: string | null;
  size: string | null;
  hobbies: string | null;
  job_position: string | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  name: string;
  surname: string;
  phone: string;
  address?: string | null;
  birthdate: string;
  dni: string;
  photo?: string | null;
  iban?: string | null;
  size?: string | null;
  hobbies?: string | null;
  job_position?: string | null;
  password: string;
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
  size?: string | null;
  hobbies?: string | null;
  job_position?: string | null;
  is_active?: boolean | null;
}

export interface UserDetails {
  id: number;
  email: string;
  name: string;
  surname: string;
  phone: string;
  address: string | null;
  birthdate: string;
  dni: string;
  photo: string | null;
  iban: string | null;
  size: string | null;
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
  capacity: number;
  price: number;
  allow_waitlist: boolean;
  entity_id: number;
  created_at: string;
  entity?: EntityResponse | null;
}

export interface ActivityCreate {
  title: string;
  description: string;
  image_url?: string | null;
  date: string;
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
}

export interface NotificationPreferencesUpdate {
  preferences: { event_type: string; in_app_enabled: boolean; email_enabled: boolean }[];
}
