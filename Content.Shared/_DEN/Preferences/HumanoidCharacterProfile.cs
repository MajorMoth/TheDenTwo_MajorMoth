using Content.Shared._DEN.Traits.Prototypes;
using Content.Shared.Chat.Prototypes;
using Content.Shared.Humanoid;
using Content.Shared.Preferences.Loadouts;
using Content.Shared.Roles;
using Content.Shared.Traits;
using JetBrains.Annotations;
using Robust.Shared.Enums;
using Robust.Shared.Prototypes;
using Robust.Shared.Utility;

namespace Content.Shared.Preferences;

public sealed partial class HumanoidCharacterProfile
{
    [DataField("_traitPreferences")]
    private HashSet<ProtoId<EntityTraitPrototype>> _entityTraitPreferences = new();

    /// <summary>
    /// <see cref="_entityTraitPreferences"/>
    /// </summary>
    public IReadOnlySet<ProtoId<EntityTraitPrototype>> EntityTraitPreferences => _entityTraitPreferences;

    public HumanoidCharacterProfile(
        string name,
        string flavortext,
        string species,
        int age,
        Sex sex,
        ProtoId<EmoteSoundsPrototype> voice,
        Gender gender,
        HumanoidCharacterAppearance appearance,
        SpawnPriorityPreference spawnPriority,
        Dictionary<ProtoId<JobPrototype>, JobPriority> jobPriorities,
        PreferenceUnavailableMode preferenceUnavailable,
        HashSet<ProtoId<AntagPrototype>> antagPreferences,
        HashSet<ProtoId<EntityTraitPrototype>> entityTraitPreferences,
        Dictionary<string, RoleLoadout> loadouts)
    {
        Name = name;
        FlavorText = flavortext;
        Species = species;
        Age = age;
        Sex = sex;
        Voice = voice;
        Gender = gender;
        Appearance = appearance;
        SpawnPriority = spawnPriority;
        _jobPriorities = jobPriorities;
        PreferenceUnavailable = preferenceUnavailable;
        _antagPreferences = antagPreferences;
        _entityTraitPreferences = entityTraitPreferences; // DEN
        _loadouts = loadouts;

        var hasHighPrority = false;
        foreach (var (key, value) in _jobPriorities)
        {
            if (value == JobPriority.Never)
                _jobPriorities.Remove(key);
            else if (value != JobPriority.High)
                continue;

            if (hasHighPrority)
                _jobPriorities[key] = JobPriority.Medium;

            hasHighPrority = true;
        }
    }

    [PublicAPI]
    public HumanoidCharacterProfile WithEntityTraitPreference(ProtoId<EntityTraitPrototype> traitId, IPrototypeManager protoManager)
    {
        // null category is assumed to be default.
        if (!protoManager.TryIndex(traitId, out var traitProto))
            return new(this);

        var category = traitProto.Category;

        // Category not found so dump it.
        TraitCategoryPrototype? traitCategory = null;
        if (category != null && !protoManager.Resolve(category, out traitCategory))
            return new(this);

        var list = new HashSet<ProtoId<EntityTraitPrototype>>(_entityTraitPreferences) { traitId };

        if (traitCategory == null || traitCategory.MaxTraitPoints < 0)
        {
            return new(this)
            {
                _entityTraitPreferences = list,
            };
        }

        var count = 0;
        foreach (var trait in list)
        {
            if (!protoManager.TryIndex(trait, out var otherProto) ||
                otherProto.Category != traitCategory)
                continue;

            count += otherProto.Cost;
        }

        if (count > traitCategory.MaxTraitPoints && traitProto.Cost != 0)
            return new(this);

        return new(this)
        {
            _entityTraitPreferences = list,
        };
    }

    [PublicAPI]
    public HumanoidCharacterProfile WithoutEntityTraitPreference(ProtoId<EntityTraitPrototype> traitId, IPrototypeManager protoManager)
    {
        var list = new HashSet<ProtoId<EntityTraitPrototype>>(_entityTraitPreferences);
        list.Remove(traitId);

        return new(this)
        {
            _entityTraitPreferences = list,
        };
    }

    /// <summary>
    /// Takes in an IEnumerable of traits and returns a List of the valid traits.
    /// </summary>
    public List<ProtoId<EntityTraitPrototype>> GetValidEntityTraits(IEnumerable<ProtoId<EntityTraitPrototype>> traits,
        IPrototypeManager protoManager)
    {
        // Track points count for each group.
        var groups = new Dictionary<string, int>();
        var result = new List<ProtoId<EntityTraitPrototype>>();

        foreach (var trait in traits)
        {
            if (!protoManager.TryIndex(trait, out var traitProto))
                continue;

            // Always valid.
            if (traitProto.Category == null)
            {
                result.Add(trait);
                continue;
            }

            // No category so dump it.
            if (!protoManager.Resolve(traitProto.Category, out var category))
                continue;

            var existing = groups.GetOrNew(category.ID);
            existing += traitProto.Cost;

            // Too expensive.
            if (existing > category.MaxTraitPoints)
                continue;

            groups[category.ID] = existing;
            result.Add(trait);
        }

        return result;
    }

}
