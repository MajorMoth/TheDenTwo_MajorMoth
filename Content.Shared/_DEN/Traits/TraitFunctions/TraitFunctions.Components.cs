using Content.Shared.Metabolism;
using Content.Shared.Whitelist;
using JetBrains.Annotations;
using Robust.Shared.Prototypes;
using Robust.Shared.Serialization.Manager;

#pragma warning disable IDE1006 // Naming Styles
namespace Content.Shared._DEN.Traits.TraitFunctions;
#pragma warning restore IDE1006 // Naming Styles

[UsedImplicitly]
public sealed partial class AddComponentTrait : ITraitFunction
{
    /// <summary>
    /// Component definitions to add to the entity.
    /// </summary>
    [DataField(required: true)] public ComponentRegistry Components { get; private set; } = [];

    /// <summary>
    /// Whether or not the components on the entity should be replaced entirely upon adding this trait.
    /// </summary>
    /// <remarks>
    /// This can be destructive if the trait is later removed.
    /// </remarks>
    [DataField] public bool RemoveExisting = false;

    [ViewVariables] public List<IComponent>? AddedComponents = null;

    public void OnTraitAdded(EntityUid owner, EntityManager entityManager)
    {
        AddedComponents = new();
        var componentFactory = IoCManager.Resolve<IComponentFactory>();
        var serialization = IoCManager.Resolve<ISerializationManager>();

        foreach (var (name, entry) in Components)
        {
            var reg = componentFactory.GetRegistration(name);

            if (entityManager.HasComponent(owner, reg) && !RemoveExisting)
                continue;

            var comp = componentFactory.GetComponent(reg);
            serialization.CopyTo(entry.Component, ref comp, notNullableOverride: true);
            entityManager.AddComponent(owner, comp, overwrite: RemoveExisting); // TODO: Check for success...?
            AddedComponents.Add(comp);
        }
    }

    public void OnTraitRemoved(EntityUid owner, EntityManager entityManager)
    {
        if (AddedComponents is null)
            return;

        foreach (var comp in AddedComponents)
        {
            if (comp.Deleted)
                continue;

            entityManager.RemoveComponent(owner, comp);
        }
    }
}

/// <summary>
///     A trait that adds a metabolizer to this entity's organs.
/// </summary>
[UsedImplicitly]
public sealed partial class AddMetabolizerTrait : ITraitFunction
{
    /// <summary>
    ///     A set of metabolizers to add to this entity's organs.
    /// </summary>
    [DataField] public HashSet<ProtoId<MetabolizerTypePrototype>> MetabolizerTypes = [];

    /// <summary>
    ///     A whitelist of allowed organs to use for this trait.
    /// </summary>
    /// <remarks>
    ///     For example: you can have this only apply to the heart or lungs by whitelisting Heart or Lung components.
    /// </remarks>
    [DataField] public EntityWhitelist? OrganWhitelist = null;

    public void OnTraitAdded(EntityUid owner, EntityManager entityManager)
    {
        var ev = new AddTraitMetabolizerEvent(MetabolizerTypes, OrganWhitelist);
        entityManager.EventBus.RaiseLocalEvent(owner, ref ev);
    }

    public void OnTraitRemoved(EntityUid owner, EntityManager entityManager)
    {
        var ev = new RemoveTraitMetabolizerEvent(MetabolizerTypes, OrganWhitelist);
        entityManager.EventBus.RaiseLocalEvent(owner, ref ev);
    }
}
