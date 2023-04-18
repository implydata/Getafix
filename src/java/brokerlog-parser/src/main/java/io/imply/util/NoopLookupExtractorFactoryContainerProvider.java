package io.imply.util;

import org.apache.druid.query.lookup.LookupExtractorFactoryContainer;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainerProvider;

import java.util.Collections;
import java.util.Optional;
import java.util.Set;

public class NoopLookupExtractorFactoryContainerProvider implements LookupExtractorFactoryContainerProvider
  {
    @Override
    public Set<String> getAllLookupNames()
    {
      return Collections.emptySet();
    }

    @Override
    public Optional<LookupExtractorFactoryContainer> get(String lookupName)
    {
      return Optional.empty();
    }
  }