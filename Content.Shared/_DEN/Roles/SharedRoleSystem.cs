using Content.Shared._DEN.Requirements.PlayerRequirements;
using JetBrains.Annotations;
using Robust.Shared.Prototypes;

namespace Content.Shared.Roles;

public abstract partial class SharedRoleSystem
{
    /// <summary>
    ///     Get a list of requirements associated with a given job.
    /// </summary>
    /// <remarks>
    ///     If a role requirement override is set for this job, the requirements associated
    ///     with the job in the override will be provided instead.
    /// </remarks>
    /// <param name="job">The job to get player requirements for.</param>
    /// <returns>The job's actual requirements, accounting for the requirement CVar.</returns>
    [PublicAPI]
    public List<IPlayerRequirement>? GetRolePlayerRequirements(JobPrototype job)
    {
        if (_requirementOverride != null
            && _requirementOverride.JobRequirements.TryGetValue(job.ID, out var overrides))
            return overrides;

        return job.PlayerRequirements;
    }

    /// <summary>
    ///     Get a list of requirements associated with a given antagonist role.
    /// </summary>
    /// <remarks>
    ///     If a role requirement override is set for this role, the requirements associated
    ///     with the role in the override will be provided instead.
    /// </remarks>
    /// <param name="antag">The antagonist role to get player requirements for.</param>
    /// <returns>The role's actual requirements, accounting for the requirement CVar.</returns>
    [PublicAPI]
    public List<IPlayerRequirement>? GetRolePlayerRequirements(AntagPrototype antag)
    {
        if (_requirementOverride != null
            && _requirementOverride.AntagRequirements.TryGetValue(antag.ID, out var overrides))
            return overrides;

        return antag.PlayerRequirements;
    }

    /// <summary>
    ///     Get a list of requirements associated with a given job.
    /// </summary>
    /// <remarks>
    ///     If a role requirement override is set for this job, the requirements associated
    ///     with the job in the override will be provided instead.
    /// </remarks>
    /// <param name="jobId">The ID of a job to get player requirements for.</param>
    /// <returns>The job's actual requirements, accounting for the requirement CVar.</returns>
    [PublicAPI]
    public List<IPlayerRequirement>? GetRolePlayerRequirements(ProtoId<JobPrototype> jobId)
    {
        return ProtoMan.TryIndex(jobId, out var job)
            ? GetRolePlayerRequirements(job)
            : null;
    }

    /// <summary>
    ///     Get a list of requirements associated with a given antagonist role.
    /// </summary>
    /// <remarks>
    ///     If a role requirement override is set for this role, the requirements associated
    ///     with the role in the override will be provided instead.
    /// </remarks>
    /// <param name="antagId">The Id of an antagonist role to get player requirements for.</param>
    /// <returns>The role's actual requirements, accounting for the requirement CVar.</returns>
    [PublicAPI]
    public List<IPlayerRequirement>? GetRolePlayerRequirements(ProtoId<AntagPrototype> antagId)
    {
        return ProtoMan.TryIndex(antagId, out var antag)
            ? GetRolePlayerRequirements(antag)
            : null;
    }
}
