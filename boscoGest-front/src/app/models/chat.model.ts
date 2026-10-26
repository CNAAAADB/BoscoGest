export interface ChatUserBrief {
  id: number;
  name: string;
  surname: string;
}

export interface ReplyBrief {
  id: number;
  sender: ChatUserBrief | null;
  preview: string;
}

export interface LastMessage {
  id: number;
  content: string;
  sender: ChatUserBrief | null;
  created_at: string;
  is_deleted: boolean;
  message_type: 'text' | 'system' | 'file';
}

export interface ConversationListItem {
  id: number;
  type: 'direct' | 'group';
  name: string | null;
  created_by_id: number | null;
  is_active: boolean;
  created_at: string;
  other_user: ChatUserBrief | null;
  last_message: LastMessage | null;
  unread_count: number;
  my_role: 'admin' | 'member' | null;
  is_muted: boolean;
  is_pinned: boolean;
}

export interface ConversationDetail {
  id: number;
  type: 'direct' | 'group';
  name: string | null;
  description: string | null;
  avatar_url: string | null;
  created_by_id: number | null;
  created_at: string;
  my_role: 'admin' | 'member' | null;
  member_count: number;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_id: number | null;
  sender: ChatUserBrief | null;
  content: string;
  message_type: 'text' | 'system' | 'file';
  reply_to: ReplyBrief | null;
  file_url: string | null;
  file_name: string | null;
  file_type: string | null;
  is_deleted: boolean;
  created_at: string;
}

export interface ChatMember {
  id: number;
  conversation_id: number;
  user_id: number;
  user: ChatUserBrief;
  role: 'admin' | 'member';
  joined_at: string;
  is_active: boolean;
  is_online: boolean;
}

export interface JoinRequest {
  id: number;
  conversation_id: number;
  user_id: number;
  user: ChatUserBrief;
  status: 'pending' | 'accepted' | 'rejected';
  requested_at: string;
  reviewed_at: string | null;
}

export interface UserSearchResult {
  id: number;
  name: string;
  surname: string;
  email: string;
}

// WebSocket payloads
export type ChatWsPayload =
  | { type: 'new_message'; conversation_id: number; message: ChatMessage }
  | { type: 'message_deleted'; conversation_id: number; message_id: number }
  | { type: 'typing'; conversation_id: number; user: ChatUserBrief }
  | { type: 'added_to_group'; conversation_id: number }
  | { type: 'removed_from_group'; conversation_id: number }
  | { type: 'join_request'; conversation_id: number; user: ChatUserBrief }
  | { type: 'join_request_accepted'; conversation_id: number }
  | { type: 'join_request_rejected'; conversation_id: number };
