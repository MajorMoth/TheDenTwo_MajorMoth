using Content.Shared._DEN.Requirements.Managers;
using Content.Shared._DEN.Requirements.PlayerRequirements;
using Content.Shared.Preferences;
using Content.Shared.Roles;
using Robust.Shared.Player;

namespace Content.Server.Players.PlayTimeTracking;

public sealed partial class PlayTimeTrackingSystem
{
    private bool PassesRequirements(ICommonSession player,
        List<IPlayerRequirement> requirements,
        PlayerRequirementContext? context = null)
    {
        context ??= _requirements.GetPlayerContext(player);
        return SharedPlayerRequirementManager.CheckRequirements(context, requirements);
    }

    private bool IsJobAllowed(ICommonSession player,
        JobPrototype job,
        PlayerRequirementContext? context = null)
    {
        context ??= _requirements.GetPlayerContext(player);
        var playTimes = context.Playtimes ?? new Dictionary<string, TimeSpan>();
        var profile = context.Profile
            ?? (HumanoidCharacterProfile?)_preferencesManager.GetPreferences(player.UserId).SelectedCharacter;

        // TODO DEN: This is deprecated.
        var oldRequirementsMet = JobRequirements.TryRequirementsMet(job,
            playTimes,
            out _,
            EntityManager,
            ProtoMan,
            profile);

        var playerReqs = _roles.GetRolePlayerRequirements(job);
        var requirementsMet = playerReqs == null || PassesRequirements(player, playerReqs, context);
        return oldRequirementsMet && requirementsMet;
    }
}
