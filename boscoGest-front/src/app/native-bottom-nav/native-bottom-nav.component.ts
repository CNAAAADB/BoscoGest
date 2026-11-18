import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { ChatService } from '../chat/chat.service';

@Component({
  selector: 'app-native-bottom-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, MatIconModule],
  templateUrl: './native-bottom-nav.component.html',
  styleUrl: './native-bottom-nav.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NativeBottomNavComponent {
  readonly unread = inject(ChatService).totalUnread;
}
