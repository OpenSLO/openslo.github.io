package schemacheck_test

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
	"testing"

	v1 "github.com/OpenSLO/go-sdk/pkg/openslo/v1"
	v1alpha "github.com/OpenSLO/go-sdk/pkg/openslo/v1alpha"
	v2alpha "github.com/OpenSLO/go-sdk/pkg/openslo/v2alpha"
	"github.com/OpenSLO/go-sdk/pkg/openslosdk"
	"github.com/nobl9/govy/pkg/govy"
)

type propertyDoc struct {
	govy.PropertyPlan
	ComponentPlans []govy.PropertyPlan `json:"componentPlans"`
}

type manifest map[string]map[string]struct {
	Properties []propertyDoc `json:"properties"`
}

func TestManifestMatchesSDK(t *testing.T) {
	data, err := os.ReadFile("../../api.json")
	if err != nil {
		t.Fatal(err)
	}
	var docs manifest
	if err := json.Unmarshal(data, &docs); err != nil {
		t.Fatal(err)
	}
	checkObject(t, docs, "openslo/v1alpha", "Service", v1alpha.Service{}.GetValidator())
	checkObject(t, docs, "openslo/v1alpha", "SLO", v1alpha.SLO{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "Service", v1.Service{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "SLO", v1.SLO{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "SLI", v1.SLI{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "AlertCondition", v1.AlertCondition{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "AlertPolicy", v1.AlertPolicy{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "AlertNotificationTarget", v1.AlertNotificationTarget{}.GetValidator())
	checkObject(t, docs, "openslo/v1", "DataSource", v1.DataSource{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "Service", v2alpha.Service{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "SLO", v2alpha.SLO{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "SLI", v2alpha.SLI{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "AlertCondition", v2alpha.AlertCondition{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "AlertPolicy", v2alpha.AlertPolicy{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "AlertNotificationTarget", v2alpha.AlertNotificationTarget{}.GetValidator())
	checkObject(t, docs, "openslo.com/v2alpha", "DataSource", v2alpha.DataSource{}.GetValidator())
	for version, objects := range docs {
		if len(objects) == 0 {
			t.Errorf("no SDK validators registered for version %s", version)
		}
		for kind := range objects {
			t.Errorf("no SDK validator registered for %s/%s", version, kind)
		}
	}
}

func TestCompleteExamplesValidate(t *testing.T) {
	paths, err := filepath.Glob("../../docs/schema/*/*.md")
	if err != nil {
		t.Fatal(err)
	}
	paths = append(paths, "../../docs/specification.md")
	fence := regexp.MustCompile("(?ms)^[ \\t]*```ya?ml[^\\n]*\\n(.*?)^[ \\t]*```")
	count := 0
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		for _, match := range fence.FindAllSubmatch(data, -1) {
			example := match[1]
			// The specification also contains schematic objects with placeholder names.
			if !bytes.Contains(example, []byte("apiVersion:")) || bytes.Contains(example, []byte("name: string")) {
				continue
			}
			count++
			objects, err := openslosdk.Decode(bytes.NewReader(example), openslosdk.FormatYAML)
			if err != nil {
				t.Errorf("decode example %d in %s: %v", count, path, err)
				continue
			}
			if err := openslosdk.Validate(objects...); err != nil {
				t.Errorf("validate example %d in %s: %v", count, path, err)
			}
		}
	}
	if count == 0 {
		t.Fatal("no complete examples found")
	}
	t.Logf("validated %d complete examples", count)
}

func checkObject[T any](t *testing.T, docs manifest, version, kind string, validator govy.Validator[T]) {
	t.Helper()
	t.Run(version+"/"+kind, func(t *testing.T) {
		doc, ok := docs[version][kind]
		if !ok {
			t.Fatal("object is missing from the manifest")
		}
		delete(docs[version], kind)
		if len(docs[version]) == 0 {
			delete(docs, version)
		}
		fields := make(map[string]bool)
		serializedFields(reflect.TypeFor[T](), "$", fields)
		properties := make(map[string]govy.PropertyPlan)
		components := make(map[string]govy.PropertyPlan)
		for _, property := range doc.Properties {
			path := property.Path.String()
			if _, duplicate := properties[path]; duplicate {
				t.Errorf("duplicate property %s", path)
			}
			properties[path] = property.PropertyPlan
			if !fields[path] {
				t.Errorf("property %s is not a serialized SDK field", path)
			}
			delete(fields, path)
			for _, component := range property.ComponentPlans {
				componentPath := component.Path.String()
				if !strings.HasPrefix(componentPath, path+".") {
					t.Errorf("component %s does not belong to %s", componentPath, path)
				}
				if _, duplicate := components[componentPath]; duplicate {
					t.Errorf("duplicate component %s", componentPath)
				}
				components[componentPath] = component
			}
		}
		for path := range fields {
			t.Errorf("serialized SDK field %s is missing from the manifest", path)
		}
		plan, err := govy.Plan(validator, govy.PlanStrictMode())
		if err != nil {
			t.Fatal(err)
		}
		ruleCount := 0
		for _, expected := range plan.Properties {
			path := expected.Path.String()
			ruleCount += len(expected.Rules)
			if actual, ok := properties[path]; ok {
				compareJSON(t, path+" rules", expected.Rules, actual.Rules)
				compareJSON(t, path+" values", expected.Values, actual.Values)
				compareJSON(t, path+" examples", expected.Examples, actual.Examples)
				delete(properties, path)
			} else if actual, ok := components[path]; ok {
				compareJSON(t, path+" component", expected, actual)
				delete(components, path)
			} else {
				t.Errorf("SDK validation path %s is missing from the manifest", path)
			}
		}
		for path, property := range properties {
			if len(property.Rules)+len(property.Values)+len(property.Examples) != 0 {
				t.Errorf("property %s has validation metadata absent from the SDK plan", path)
			}
		}
		for path := range components {
			t.Errorf("component %s is absent from the SDK plan or duplicates a field", path)
		}
		t.Logf("checked %d properties and %d SDK rules", len(doc.Properties), ruleCount)
	})
}

func compareJSON(t *testing.T, label string, expected, actual any) {
	t.Helper()
	want, err := json.Marshal(expected)
	if err != nil {
		t.Fatal(err)
	}
	got, err := json.Marshal(actual)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(want) {
		t.Errorf("%s differ:\nSDK: %s\nmanifest: %s", label, want, got)
	}
}

func serializedFields(value reflect.Type, path string, fields map[string]bool) {
	for value.Kind() == reflect.Pointer {
		value = value.Elem()
	}
	fields[path] = true
	// Raw JSON and durations serialize as a single value, without exported children.
	if value == reflect.TypeFor[json.RawMessage]() || value == reflect.TypeFor[v1.DurationShorthand]() || value == reflect.TypeFor[v2alpha.DurationShorthand]() {
		return
	}
	switch value.Kind() {
	case reflect.Struct:
		for _, field := range reflect.VisibleFields(value) {
			if !field.IsExported() {
				continue
			}
			name, _, _ := strings.Cut(field.Tag.Get("json"), ",")
			if name == "-" {
				continue
			}
			if name == "" {
				// VisibleFields already includes an embedded struct's promoted fields.
				if field.Anonymous {
					continue
				}
				name = field.Name
			}
			serializedFields(field.Type, path+"."+name, fields)
		}
	case reflect.Slice, reflect.Array:
		serializedFields(value.Elem(), path+"[*]", fields)
	case reflect.Map:
		serializedFields(value.Key(), path+".*~", fields)
		serializedFields(value.Elem(), path+".*", fields)
	}
}
