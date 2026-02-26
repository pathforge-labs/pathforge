"use client";

import { useState, useCallback, type FormEvent } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserProfile, useUpdateProfile, useRequestDataExport } from "@/hooks/api/use-user-profile";

/* ── Page Component ───────────────────────────────────────── */

export default function DashboardSettingsPage() {
  const profile = useUserProfile();
  const updateProfile = useUpdateProfile();
  const requestExport = useRequestDataExport();

  const [formData, setFormData] = useState({
    headline: "",
    bio: "",
    location: "",
    phone: "",
    linkedin_url: "",
    github_url: "",
    website_url: "",
  });
  const [isEditing, setIsEditing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const startEditing = useCallback(() => {
    if (profile.data) {
      setFormData({
        headline: profile.data.headline ?? "",
        bio: profile.data.bio ?? "",
        location: profile.data.location ?? "",
        phone: profile.data.phone ?? "",
        linkedin_url: profile.data.linkedin_url ?? "",
        github_url: profile.data.github_url ?? "",
        website_url: profile.data.website_url ?? "",
      });
    }
    setIsEditing(true);
    setSaveSuccess(false);
  }, [profile.data]);

  const cancelEditing = useCallback(() => {
    setIsEditing(false);
    setSaveSuccess(false);
  }, []);

  const handleSave = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      setSaveSuccess(false);

      try {
        await updateProfile.mutateAsync(formData);
        setIsEditing(false);
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } catch {
        // Error handled by TanStack Query mutation state
      }
    },
    [formData, updateProfile],
  );

  const handleExport = useCallback(async () => {
    setExportSuccess(false);
    try {
      await requestExport.mutateAsync({ export_format: "json" });
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 5000);
    } catch {
      // Error handled by TanStack Query mutation state
    }
  }, [requestExport]);

  const updateField = useCallback(
    (field: keyof typeof formData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your profile and account preferences.
        </p>
      </div>

      {/* Profile Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Profile Information</CardTitle>
              <CardDescription>Your public career profile details</CardDescription>
            </div>
            {!isEditing && (
              <Button variant="outline" size="sm" onClick={startEditing}>
                Edit Profile
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {profile.isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-5 w-64" />
              <Skeleton className="h-5 w-40" />
            </div>
          ) : profile.error ? (
            <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-600 dark:text-yellow-400">
              <p className="font-medium">Could not load profile</p>
              <p className="mt-1 text-xs">{profile.error.message}</p>
            </div>
          ) : isEditing ? (
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="headline">Headline</Label>
                  <Input
                    id="headline"
                    placeholder="e.g. Senior Software Engineer"
                    value={formData.headline}
                    onChange={(event) => updateField("headline", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    placeholder="e.g. Amsterdam, NL"
                    value={formData.location}
                    onChange={(event) => updateField("location", event.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="bio">Bio</Label>
                <textarea
                  id="bio"
                  placeholder="Tell us about yourself…"
                  value={formData.bio}
                  onChange={(event) => updateField("bio", event.target.value)}
                  className="min-h-[80px] w-full rounded-lg border border-border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="+31 6 1234 5678"
                    value={formData.phone}
                    onChange={(event) => updateField("phone", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                  <Input
                    id="linkedin_url"
                    type="url"
                    placeholder="https://linkedin.com/in/…"
                    value={formData.linkedin_url}
                    onChange={(event) => updateField("linkedin_url", event.target.value)}
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="github_url">GitHub URL</Label>
                  <Input
                    id="github_url"
                    type="url"
                    placeholder="https://github.com/…"
                    value={formData.github_url}
                    onChange={(event) => updateField("github_url", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="website_url">Website URL</Label>
                  <Input
                    id="website_url"
                    type="url"
                    placeholder="https://example.com"
                    value={formData.website_url}
                    onChange={(event) => updateField("website_url", event.target.value)}
                  />
                </div>
              </div>

              {/* Save Error */}
              {updateProfile.error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
                  {updateProfile.error.message}
                </div>
              )}

              <div className="flex items-center gap-2">
                <Button type="submit" disabled={updateProfile.isPending}>
                  {updateProfile.isPending ? "Saving…" : "Save Changes"}
                </Button>
                <Button type="button" variant="outline" onClick={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            /* Read-only view */
            <div className="space-y-3">
              <ProfileField label="Headline" value={profile.data?.headline} />
              <ProfileField label="Location" value={profile.data?.location} />
              <ProfileField label="Bio" value={profile.data?.bio} />
              <ProfileField label="Phone" value={profile.data?.phone} />
              <ProfileField label="LinkedIn" value={profile.data?.linkedin_url} isLink />
              <ProfileField label="GitHub" value={profile.data?.github_url} isLink />
              <ProfileField label="Website" value={profile.data?.website_url} isLink />
              {saveSuccess && (
                <Badge variant="default" className="bg-green-600 text-xs">
                  ✓ Profile saved
                </Badge>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Separator />

      {/* Data & Privacy Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Data & Privacy</CardTitle>
          <CardDescription>
            Manage your data in compliance with GDPR regulations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* GDPR Data Export */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
            <div>
              <p className="text-sm font-medium">Export Your Data</p>
              <p className="text-xs text-muted-foreground">
                Download all your data in JSON format (GDPR Art. 20)
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={requestExport.isPending}
            >
              {requestExport.isPending ? "Requesting…" : "Request Export"}
            </Button>
          </div>

          {/* Export feedback */}
          {exportSuccess && (
            <div className="rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3 text-sm text-green-600 dark:text-green-400">
              Export requested successfully. You will receive a download link when ready.
            </div>
          )}
          {requestExport.error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
              {requestExport.error.message}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────────── */

function ProfileField({
  label,
  value,
  isLink = false,
}: {
  readonly label: string;
  readonly value: string | null | undefined;
  readonly isLink?: boolean;
}) {
  return (
    <div>
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {value ? (
        isLink ? (
          <a
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 block text-sm text-primary underline-offset-4 hover:underline"
          >
            {value}
          </a>
        ) : (
          <p className="mt-0.5 text-sm">{value}</p>
        )
      ) : (
        <p className="mt-0.5 text-sm text-muted-foreground/50">Not set</p>
      )}
    </div>
  );
}
