/**
 * PathForge — Notifications Dashboard Page
 * ===========================================
 * Notification list, digest history, preferences.
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useNotifications,
  useUnreadNotificationCount,
  useMarkAllNotificationsRead,
} from "@/hooks/api/use-notifications";

/* ── Page Component ───────────────────────────────────────── */

export default function NotificationsPage(): React.JSX.Element {
  const { data: notifications, isLoading } = useNotifications();
  const { data: unreadCount } = useUnreadNotificationCount();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Notifications
            {unreadCount?.total_unread != null && unreadCount.total_unread > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                {unreadCount.total_unread}
              </span>
            )}
          </h1>
          <p className="text-sm text-muted-foreground">
            Engine-aware notifications with severity and digest scheduling
          </p>
        </div>
        <Button
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending || (unreadCount?.total_unread ?? 0) === 0}
          size="sm"
          variant="outline"
        >
          {markAllRead.isPending ? "Marking…" : "✓ Mark All Read"}
        </Button>
      </div>

      {/* Notification List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🔔 Recent Notifications</CardTitle>
          <CardDescription>Alerts and updates from your intelligence engines</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : notifications?.items?.length ? (
            <div className="space-y-3">
              {notifications.items.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex items-start gap-3 rounded-lg border p-4 ${
                    !notification.is_read ? "bg-primary/5 border-primary/20" : ""
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        notification.severity === "critical" ? "bg-red-100 text-red-800" :
                        notification.severity === "warning" ? "bg-orange-100 text-orange-800" :
                        notification.severity === "success" ? "bg-green-100 text-green-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {notification.severity}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {notification.source_engine}
                      </span>
                    </div>
                    <p className="font-medium text-sm mt-1">{notification.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{notification.message}</p>
                  </div>
                  <p className="text-xs text-muted-foreground whitespace-nowrap">
                    {notification.created_at}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No notifications yet. Your intelligence engines will send alerts here.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
