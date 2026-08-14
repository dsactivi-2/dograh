"use client";

import {
  BarChart3,
  AlertTriangle,
  ArrowUpCircle,
  AudioLines,
  Brain,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  ClipboardCheck,
  Database,
  FileCode2,
  FileText,
  FlaskConical,
  GraduationCap,
  Home,
  Key,
  LogOut,
  type LucideIcon,
  Megaphone,
  Phone,
  Radar,
  Settings,
  TrendingUp,
  UserRound,
  Wallet,
  Workflow,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React from "react";

import { BrandLogo } from "@/components/BrandLogo";
import { SidebarTeamSwitcher } from "@/components/layout/SidebarTeamSwitcher";
import ThemeToggle from "@/components/ThemeSwitcher";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAppConfig } from "@/context/AppConfigContext";
import { useLeadForms } from "@/context/LeadFormsContext";
import { useTelephonyConfigWarnings } from "@/context/TelephonyConfigWarningsContext";
import { useLatestReleaseVersion } from "@/hooks/useLatestReleaseVersion";
import type { LocalUser } from "@/lib/auth";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

type SidebarNavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
  showsTelephonyWarning?: boolean;
};

type SidebarNavSection = {
  label?: string;
  items: SidebarNavItem[];
};

const TELEPHONY_WARNING_COPY = "Action required";

const NAV_SECTIONS: SidebarNavSection[] = [
  {
    items: [
      {
        title: "Overview",
        url: "/overview",
        icon: Home,
      },
    ],
  },
  {
    label: "BUILD",
    items: [
      {
        title: "Voice Agents",
        url: "/workflow",
        icon: Workflow,
      },
      {
        title: "Campaigns",
        url: "/campaigns",
        icon: Megaphone,
      },
      {
        title: "Models",
        url: "/model-configurations",
        icon: Brain,
      },
      {
        title: "Telephony",
        url: "/telephony-configurations",
        icon: Phone,
        showsTelephonyWarning: true,
      },
      {
        title: "Tools",
        url: "/tools",
        icon: Wrench,
      },
      {
        title: "Files",
        url: "/files",
        icon: Database,
      },
      {
        title: "Recordings",
        url: "/recordings",
        icon: AudioLines,
      },
      {
        title: "Developers",
        url: "/api-keys",
        icon: Key,
      },
    ],
  },
  {
    label: "MANAGE",
    items: [
      {
        title: "Agent Runs",
        url: "/usage",
        icon: TrendingUp,
      },
      {
        title: "Billing",
        url: "/billing",
        icon: CircleDollarSign,
      },
      {
        title: "Analytics",
        url: "/analytics",
        icon: BarChart3,
      },
      {
        title: "Campaign Ops",
        url: "/campaigns/ops",
        icon: Radar,
      },
      {
        title: "Costs",
        url: "/costs",
        icon: Wallet,
      },
      {
        title: "QA Center",
        url: "/qa-center",
        icon: ClipboardCheck,
      },
      {
        title: "Training",
        url: "/training",
        icon: GraduationCap,
      },
      {
        title: "Scripts",
        url: "/scripts",
        icon: FileCode2,
      },
      {
        title: "Evals",
        url: "/evals",
        icon: FlaskConical,
      },
      {
        title: "Reports",
        url: "/reports",
        icon: FileText,
      }
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { state, isMobile, setOpenMobile } = useSidebar();
  const { provider, logout, user } = useAuth();
  const { config } = useAppConfig();
  const { openHireExpert } = useLeadForms();
  const {
    telnyxMissingWebhookPublicKeyCount,
    vonageMissingSignatureSecretCount,
  } = useTelephonyConfigWarnings();
  const hasTelephonyWarning =
    telnyxMissingWebhookPublicKeyCount > 0 ||
    vonageMissingSignatureSecretCount > 0;
  const isCollapsed = !isMobile && state === "collapsed";

  // Version info from app config context
  const versionInfo = config ? { ui: config.uiVersion, api: config.apiVersion } : null;

  // Check for updates only on self-hosted (OSS) deployments — cloud is managed for the user.
  const { latest: latestRelease, isBehind, isLatest } = useLatestReleaseVersion(
    versionInfo?.ui,
    { enabled: config?.deploymentMode === "oss" },
  );

  const isActive = (path: string) => {
    // Keep /campaigns and /campaigns/ops from both highlighting.
    if (path === "/campaigns") {
      return (
        pathname === "/campaigns" ||
        (pathname.startsWith("/campaigns/") &&
          !pathname.startsWith("/campaigns/ops"))
      );
    }
    if (path === "/campaigns/ops") {
      return pathname.startsWith("/campaigns/ops");
    }
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  const handleMobileNavClick = () => {
    if (isMobile) {
      setOpenMobile(false);
    }
  };

  const SidebarLink = ({ item }: { item: SidebarNavItem }) => {
    const isItemActive = isActive(item.url);
    const Icon = item.icon;
    const showWarningDot = item.showsTelephonyWarning && hasTelephonyWarning;
    const tooltip = {
      children: (
        <div className="notranslate" translate="no">
          <p>{item.title}</p>
          {showWarningDot && (
            <p className="text-amber-600 dark:text-amber-400">{TELEPHONY_WARNING_COPY}</p>
          )}
        </div>
      ),
      // Match the hover-expand flyout delay so the tooltip doesn't flash
      // while the user is mid-hover toward the flyout.
      delayDuration: 400,
      // Keep the tooltip clear of the flyout so they don't stack.
      side: "bottom" as const,
      align: "start" as const,
      hidden: !isCollapsed,
    };

    return (
      <SidebarMenuItem key={item.title}>
        <SidebarMenuButton
          asChild
          isActive={isItemActive}
          tooltip={tooltip}
          className={cn(
            "h-9 rounded-lg px-2.5 text-[13px] font-medium transition-colors",
            isItemActive
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
            isCollapsed && "justify-center px-0",
          )}
        >
          <Link
            href={item.url}
            onClick={handleMobileNavClick}
            className={cn(
              "flex w-full items-center notranslate",
              isCollapsed ? "justify-center gap-0" : "gap-2.5",
            )}
            translate="no"
          >
            <span className="relative shrink-0">
              <Icon className="h-4 w-4" />
              {showWarningDot && (
                <span
                  aria-hidden
                  className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-amber-500 ring-2 ring-sidebar"
                />
              )}
            </span>
            <span
              className={cn(
                "truncate transition-opacity duration-200",
                isCollapsed ? "sr-only w-0 opacity-0" : "opacity-100",
              )}
            >
              {item.title}
            </span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  };

  // Footer identity trigger: avatar initials only (no name), in a subtle
  // muted chip. Hover/open lifts the chip so it reads as interactive without
  // looking like a primary button.
  const UserMenu = ({ localUser }: { localUser: LocalUser }) => {
    const initials = (localUser.email?.[0] ?? "?").toUpperCase();
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label="Account menu"
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
              "bg-muted text-[11px] font-semibold uppercase tracking-wide text-muted-foreground",
              "ring-1 ring-border/60 transition-colors",
              "hover:bg-muted/80 hover:text-foreground hover:ring-border",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "data-[state=open]:bg-muted/80 data-[state=open]:text-foreground data-[state=open]:ring-border",
            )}
          >
            {initials}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side="top"
          align="start"
          sideOffset={8}
          className="w-64"
        >
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col gap-0.5">
              <span className="truncate text-sm font-medium text-foreground">
                {localUser.email}
              </span>
              {localUser.is_superuser ? (
                <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Superuser
                </span>
              ) : null}
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onSelect={() => router.push("/settings")}
            className="gap-2"
          >
            <Settings className="h-4 w-4" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => logout()}
            className="gap-2 text-destructive focus:text-destructive"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  };

  return (
    <Sidebar
      collapsible="icon"
      className="border-r border-sidebar-border bg-sidebar text-sidebar-foreground"
    >
      <SidebarHeader
        className={cn(
          "flex flex-row items-center border-b border-sidebar-border",
          isCollapsed
            ? "h-14 justify-center gap-0 px-0 py-0"
            : "h-14 justify-between gap-1 px-3",
        )}
      >
        <Link
          href="/overview"
          onClick={handleMobileNavClick}
          aria-label="Dograh home"
          className={cn(
            "flex items-center rounded-md outline-none ring-sidebar-ring focus-visible:ring-2",
            isCollapsed ? "justify-center" : "min-w-0 flex-1",
          )}
        >
          <BrandLogo
            className={cn(
              "text-sidebar-foreground transition-all",
              isCollapsed ? "h-5 w-5" : "h-7 w-auto max-w-[128px]",
            )}
          />
        </Link>
        {!isCollapsed && (
          <SidebarTrigger className="h-7 w-7 shrink-0 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
        )}
      </SidebarHeader>

      {isCollapsed && (
        <div className="flex items-center justify-center border-b border-sidebar-border py-2">
          <SidebarTrigger className="h-7 w-7 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
        </div>
      )}

      {/* Team switcher — sits under the brand so the active workspace is
          always visible. Renders nothing when the user has ≤1 org. */}
      <SidebarTeamSwitcher isCollapsed={isCollapsed} />

      <SidebarContent className={cn("py-3", isCollapsed ? "px-1.5" : "px-2")}>
        {NAV_SECTIONS.map((section, idx) => (
          <SidebarGroup key={section.label ?? `section-${idx}`} className="p-0 mb-4 last:mb-0">
            {section.label && !isCollapsed && (
              <SidebarGroupLabel className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/40">
                {section.label}
              </SidebarGroupLabel>
            )}
            {section.label && isCollapsed && (
              <div className="mx-auto mb-2 h-px w-5 bg-sidebar-border" />
            )}
            <SidebarMenu className="gap-0.5">
              {section.items.map((item) => (
                <SidebarLink key={item.url} item={item} />
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter
        className={cn(
          "border-t border-sidebar-border",
          isCollapsed ? "items-center gap-2 px-1.5 py-2.5" : "gap-1.5 px-2 py-2.5",
        )}
      >
        {/* Secondary actions — muted, compact. Collapse control only shows
            when the rail is icon-mode (expanded uses the header chevron). */}
        <div
          className={cn(
            "flex items-center",
            isCollapsed ? "flex-col gap-1" : "justify-between gap-1",
          )}
        >
          <div className={cn("flex items-center", isCollapsed ? "flex-col gap-1" : "gap-0.5")}>
            {isCollapsed && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <SidebarTrigger className="h-7 w-7 text-sidebar-foreground/55 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  Expand sidebar
                </TooltipContent>
              </Tooltip>
            )}
            <ThemeToggle className="h-7 w-7 text-sidebar-foreground/55 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" />
          </div>
          {versionInfo && !isCollapsed && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => {
                    if (isBehind && latestRelease?.htmlUrl) {
                      window.open(latestRelease.htmlUrl, "_blank", "noopener,noreferrer");
                    }
                  }}
                  className={cn(
                    "flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[10px] tabular-nums transition-colors",
                    isBehind
                      ? "cursor-pointer text-amber-600 hover:bg-amber-500/10 dark:text-amber-400"
                      : "cursor-default text-sidebar-foreground/40",
                  )}
                >
                  {isBehind ? (
                    <ArrowUpCircle className="h-3 w-3 shrink-0" />
                  ) : null}
                  <span>
                    {versionInfo.ui === versionInfo.api
                      ? `v${versionInfo.ui}`
                      : `ui ${versionInfo.ui} · api ${versionInfo.api}`}
                  </span>
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[220px] text-xs">
                {isBehind && latestRelease ? (
                  <div className="space-y-1">
                    <p className="font-medium text-amber-600 dark:text-amber-400">
                      Update available: v{latestRelease.version}
                    </p>
                    <p className="text-muted-foreground">
                      Click to view the release. Pull the latest image and restart to upgrade.
                    </p>
                  </div>
                ) : isLatest ? (
                  <p>You're on the latest version</p>
                ) : (
                  <div className="space-y-0.5">
                    <p>UI v{versionInfo.ui}</p>
                    <p>API v{versionInfo.api}</p>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Hire-an-expert — quiet text affordance, not a sales banner. */}
        {!isCollapsed && (
          <button
            type="button"
            onClick={() => openHireExpert("sidebar")}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left",
              "text-[12px] text-sidebar-foreground/50 transition-colors",
              "hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
            )}
          >
            <UserRound className="h-3.5 w-3.5 shrink-0 opacity-70" />
            <span className="truncate">Hire an expert</span>
          </button>
        )}
        {isCollapsed && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label="Hire an expert"
                onClick={() => openHireExpert("sidebar")}
                className="flex h-7 w-7 items-center justify-center rounded-md text-sidebar-foreground/50 transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              >
                <UserRound className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={8}>
              Hire an expert
            </TooltipContent>
          </Tooltip>
        )}

        {/* Identity — avatar chip only. Email lives in the dropdown. */}
        {provider === "local" && user ? (
          isCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <UserMenu localUser={user} />
                </div>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                {user.email}
              </TooltipContent>
            </Tooltip>
          ) : (
            <div className="flex items-center gap-2 px-1 pt-0.5">
              <UserMenu localUser={user} />
              <span className="min-w-0 flex-1 truncate text-[12px] text-sidebar-foreground/55">
                {user.email}
              </span>
            </div>
          )
        ) : null}
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
