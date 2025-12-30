# PWA Feature Analysis for Peptide AI

## Executive Summary

PWAs can deliver 90%+ of native app functionality. For Peptide AI, the key opportunities are:
1. **Push Notifications** - Journey reminders, new research alerts
2. **Offline Support** - Read saved research, view stack
3. **Badging** - Unread insights, pending tasks
4. **Web Share** - Share insights with friends

---

## Current Status

### Completed Features
- [x] Service Worker with caching (`sw.js` v3)
- [x] Web App Manifest with all required fields
- [x] Install prompts (iOS overlay + Android `beforeinstallprompt`)
- [x] Dynamic PNG app icons (via Next.js ImageResponse)
- [x] App Shortcuts in manifest (Chat, Stack, Journey)
- [x] Update detection + toast notification
- [x] `appinstalled` event tracking
- [x] Display mode change detection
- [x] Apple touch icon (PNG, not SVG)
- [x] Viewport fit cover for iOS

### Next Up
- [ ] **Push Notifications** - Backend + frontend infrastructure
- [ ] **Badging API** - Show unread count on app icon
- [ ] **Native CSS Polish** - overscroll, safe-area, tap highlight
- [ ] **Enhanced Offline** - Cache conversations/stack for offline

---

## Feature Matrix

| Feature | iOS Support | Android Support | Status | Priority |
|---------|-------------|-----------------|--------|----------|
| **Push Notifications** | iOS 16.4+ (Home Screen only) | Full | TODO | HIGH |
| **Badging API** | iOS 16.4+ | Full | TODO | HIGH |
| **Offline Mode** | Full | Full | Partial | HIGH |
| **Native CSS** | Full | Full | TODO | MEDIUM |
| **App Shortcuts** | Limited | Full | DONE | - |
| **Web Share** | Full | Full | TODO | MEDIUM |
| **Share Target** | No | Full | TODO | LOW |
| **Screen Wake Lock** | iOS 16.4+ | Full | TODO | LOW |

---

## Priority 1: Push Notifications

**Why:** Highest engagement impact - journey reminders will bring users back daily.

**iOS Requirements (Critical):**
- Only works when PWA is **installed to Home Screen** (not in Safari)
- Uses Apple Push Notification Service
- Must allowlist `*.push.apple.com` for server endpoints

### Backend Work Needed

```python
# api/routes/push.py

from fastapi import APIRouter, Depends
from pywebpush import webpush, WebPushException
import os

router = APIRouter(prefix="/push", tags=["push"])

# Generate once: vapid keys
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {"sub": "mailto:support@peptide.ai"}

@router.get("/vapid-key")
async def get_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}

@router.post("/subscribe")
async def subscribe(subscription: dict, user_id: str = Depends(get_current_user)):
    # Store in MongoDB
    await db.push_subscriptions.update_one(
        {"user_id": user_id},
        {"$set": {"subscription": subscription, "updated_at": datetime.utcnow()}},
        upsert=True
    )
    return {"status": "subscribed"}

@router.post("/unsubscribe")
async def unsubscribe(user_id: str = Depends(get_current_user)):
    await db.push_subscriptions.delete_one({"user_id": user_id})
    return {"status": "unsubscribed"}

# Internal function to send push
async def send_push_notification(user_id: str, title: str, body: str, url: str = "/chat"):
    sub = await db.push_subscriptions.find_one({"user_id": user_id})
    if not sub:
        return False

    try:
        webpush(
            subscription_info=sub["subscription"],
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        return True
    except WebPushException as e:
        if e.response.status_code == 410:  # Gone - subscription expired
            await db.push_subscriptions.delete_one({"user_id": user_id})
        return False
```

### Frontend Work Needed

```typescript
// hooks/usePushNotifications.ts

export function usePushNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>('default')
  const [isSubscribed, setIsSubscribed] = useState(false)

  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission)
    }
    checkSubscription()
  }, [])

  const checkSubscription = async () => {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    setIsSubscribed(!!subscription)
  }

  const subscribe = async () => {
    const permission = await Notification.requestPermission()
    setPermission(permission)

    if (permission !== 'granted') return false

    const registration = await navigator.serviceWorker.ready
    const vapidKey = await fetch('/api/push/vapid-key').then(r => r.json())

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey.publicKey)
    })

    await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription)
    })

    setIsSubscribed(true)
    return true
  }

  return { permission, isSubscribed, subscribe }
}
```

### Service Worker Handler

```javascript
// Add to sw.js

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {}

  event.waitUntil(
    self.registration.showNotification(data.title || 'Peptide AI', {
      body: data.body,
      icon: '/api/icon/192',
      badge: '/api/icon/192',
      data: { url: data.url || '/chat' },
      vibrate: [200, 100, 200]
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // Focus existing window or open new
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus()
          client.navigate(event.notification.data.url)
          return
        }
      }
      return clients.openWindow(event.notification.data.url)
    })
  )
})
```

### Use Cases for Peptide AI
| Trigger | Title | Body | When |
|---------|-------|------|------|
| Journey reminder | "Time to log!" | "How are you feeling today?" | 9am daily |
| Missed entry | "Don't break your streak!" | "You haven't logged in 2 days" | After 48h |
| Stack suggestion | "Stack insight" | "Based on your goals, consider..." | Weekly |
| Research alert | "New research" | "New study on [peptide]" | On publish |

---

## Priority 2: Badging API

**Why:** Quick win, high visibility, reinforces engagement.

```typescript
// lib/badging.ts

export async function setAppBadge(count: number) {
  if ('setAppBadge' in navigator) {
    if (count > 0) {
      await navigator.setAppBadge(count)
    } else {
      await navigator.clearAppBadge()
    }
  }
}

// Usage in ChatContainer.tsx
useEffect(() => {
  const unreadCount = conversations.filter(c => c.hasUnread).length
  setAppBadge(unreadCount)
}, [conversations])
```

---

## Priority 3: Native CSS Polish

Add to `globals.css`:

```css
/* Disable pull-to-refresh (prevents accidental refresh) */
html, body {
  overscroll-behavior-y: contain;
}

/* Safe area insets for notch/home indicator */
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.safe-area-top {
  padding-top: env(safe-area-inset-top, 0);
}

/* Disable tap highlight on interactive elements */
button, a, [role="button"] {
  -webkit-tap-highlight-color: transparent;
}

/* Disable text selection on UI elements (not content) */
.no-select {
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
}

/* Smooth momentum scrolling */
.scroll-container {
  -webkit-overflow-scrolling: touch;
}

/* Prevent zoom on input focus (iOS) */
input, textarea, select {
  font-size: 16px; /* Prevents iOS zoom */
}
```

---

## Priority 4: Enhanced Offline Support

**Current state:** Basic caching of static assets.
**Goal:** Cache user data for offline viewing.

```javascript
// Enhanced sw.js caching

// Cache user-specific data when online
self.addEventListener('message', async (event) => {
  if (event.data.type === 'CACHE_USER_DATA') {
    const cache = await caches.open('user-data-v1')
    const { userId } = event.data

    // Cache stack
    const stackRes = await fetch(`/api/stack?user_id=${userId}`)
    if (stackRes.ok) {
      await cache.put(`/api/stack?user_id=${userId}`, stackRes.clone())
    }

    // Cache recent conversations (summaries)
    const convosRes = await fetch(`/api/conversations?user_id=${userId}&limit=20`)
    if (convosRes.ok) {
      await cache.put(`/api/conversations?user_id=${userId}`, convosRes.clone())
    }
  }
})

// Serve cached data when offline
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // For API calls - try network, fall back to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Clone and cache successful GET responses
          if (event.request.method === 'GET' && response.ok) {
            const clone = response.clone()
            caches.open('user-data-v1').then(cache => {
              cache.put(event.request, clone)
            })
          }
          return response
        })
        .catch(() => caches.match(event.request))
    )
    return
  }
  // ... rest of fetch handler
})
```

---

## iOS-Specific Considerations

### What Works on iOS 16.4+:
- Push notifications (Home Screen only)
- Badging API
- Screen Wake Lock
- Offline caching
- Display: standalone
- Web Share (sending)

### What Doesn't Work on iOS:
- Share Target (can't receive shared content)
- App Shortcuts (long-press menu)
- Vibration API
- Background Sync
- File Handlers

### iOS PWA Gotchas:
1. **Must be on Home Screen** for push notifications
2. **No background fetch** - sync happens when app opens
3. **Limited storage** - Safari may evict cached data after 7 days of no use
4. **No install prompt** - must guide users manually (our InstallHint)

---

## Implementation Checklist

### Phase 1: Foundation ✅ COMPLETE
- [x] Service Worker with versioned caching
- [x] Web App Manifest (name, icons, display, shortcuts)
- [x] Install prompts (iOS overlay + Android native)
- [x] Dynamic PNG app icons
- [x] Update detection + toast
- [x] appinstalled tracking
- [x] Apple touch icon fix

### Phase 2: Engagement (NEXT)
- [ ] Push Notifications
  - [ ] Generate VAPID keys
  - [ ] Backend routes (subscribe, unsubscribe, send)
  - [ ] Frontend hook (usePushNotifications)
  - [ ] SW push handler
  - [ ] Settings UI for enable/disable
  - [ ] Journey reminder scheduler
- [ ] Badging API
  - [ ] Badge utility function
  - [ ] Integration with unread state

### Phase 3: Polish
- [ ] Native CSS patterns (globals.css)
- [ ] Enhanced offline caching
- [ ] Web Share for insights

### Phase 4: Nice-to-Have
- [ ] Share Target (Android only)
- [ ] Screen Wake Lock for voice
- [ ] Haptic feedback (Android)

---

## Next Steps

**Recommended:** Start with Push Notifications since it has the highest engagement impact for a health/wellness app like Peptide AI. Journey reminders will drive daily active usage.

**Quick wins to do first:**
1. Add native CSS patterns (10 min)
2. Add Badging API utility (10 min)
3. Then tackle Push Notifications (larger effort)
