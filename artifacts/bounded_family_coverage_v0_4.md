# PlanSpace bounded reference-family coverage v0.1

Evidence status: `bounded_symbolic_family_coverage_pending_semantic_review`.

## Exhaustive bounded subset

- Queue tasks: 100
- Exhaustively analyzed within the declared bounds: 75
- Bounded first-goal simple paths: 3145
- Paths covered by constructed reference families: 1965
- Micro coverage: 62.48%
- Tasks with full bounded coverage: 53

## Tasks with bounded coverage below 100%

| Task | Valid paths | Covered | Coverage | Outside family |
| --- | ---: | ---: | ---: | ---: |
| `opening_windows/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `set_up_a_home_office_in_your_garage/problem0.bddl` | 180 | 24 | 13.33% | 156 |
| `moving_boxes_to_storage/problem0.bddl` | 4 | 2 | 50.00% | 2 |
| `opening_doors/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `installing_a_printer/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `dispose_of_a_pizza_box/problem0.bddl` | 3 | 1 | 33.33% | 2 |
| `installing_a_fax_machine/problem0.bddl` | 4 | 2 | 50.00% | 2 |
| `unpacking_hobby_equipment/problem0.bddl` | 240 | 120 | 50.00% | 120 |
| `carrying_in_groceries/problem0.bddl` | 6 | 4 | 66.67% | 2 |
| `fold_a_tortilla/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `loading_the_car/problem0.bddl` | 8 | 3 | 37.50% | 5 |
| `recycling_glass_bottles/problem0.bddl` | 4 | 2 | 50.00% | 2 |
| `organizing_art_supplies/problem0.bddl` | 120 | 24 | 20.00% | 96 |
| `unloading_shopping_from_car/problem0.bddl` | 138 | 48 | 34.78% | 90 |
| `lighting_fireplace/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `packing_cleaning_suppies_into_car/problem0.bddl` | 40 | 5 | 12.50% | 35 |
| `dispose_of_batteries/problem0.bddl` | 12 | 2 | 16.67% | 10 |
| `make_rose_centerpieces/problem0.bddl` | 24 | 6 | 25.00% | 18 |
| `paying_for_purchases/problem0.bddl` | 2 | 1 | 50.00% | 1 |
| `organizing_school_stuff/problem0.bddl` | 720 | 120 | 16.67% | 600 |
| `store_tulip_bulbs/problem0.bddl` | 12 | 2 | 16.67% | 10 |
| `organizing_file_cabinet/problem0.bddl` | 144 | 120 | 83.33% | 24 |

The only incomplete case uses an existential refrigerator binding while a separate concrete refrigerator has a negative open-state goal. The extra bounded paths insert goal-irrelevant open/close actions around an otherwise valid wildcard-binding plan; the constructed families intentionally retain causal representatives rather than all nonminimal detours.

## Boundary

Completeness applies only to first goal-reaching simple symbolic paths within each reported depth bound. It neither covers arbitrary nonminimal loops nor validates the real-world faithfulness of the action abstraction.
