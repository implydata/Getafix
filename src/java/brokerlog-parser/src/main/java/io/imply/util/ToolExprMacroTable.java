package io.imply.util;

import com.google.common.collect.ImmutableList;
import org.apache.druid.math.expr.ExprMacroTable;

import org.apache.druid.query.expression.*;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainer;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainerProvider;

import java.util.Optional;
import java.util.Set;

public class ToolExprMacroTable extends ExprMacroTable
{
  public static final ExprMacroTable INSTANCE = new ToolExprMacroTable();

  public ToolExprMacroTable()
  {
    super(
        ImmutableList.of(
            new IPv4AddressMatchExprMacro(),
            new IPv4AddressParseExprMacro(),
            new IPv4AddressStringifyExprMacro(),
            new LikeExprMacro(),
            new RegexpExtractExprMacro(),
            new TimestampCeilExprMacro(),
            new TimestampExtractExprMacro(),
            new TimestampFloorExprMacro(),
            new TimestampFormatExprMacro(),
            new TimestampParseExprMacro(),
            new TimestampShiftExprMacro(),
            new TrimExprMacro.BothTrimExprMacro(),
            new TrimExprMacro.LeftTrimExprMacro(),
            new TrimExprMacro.RightTrimExprMacro(),
            new NestedDataExpressions.JsonKeysExprMacro(),
            new NestedDataExpressions.JsonObjectExprMacro(),
            new NestedDataExpressions.JsonPathsExprMacro(),
            new NestedDataExpressions.JsonQueryExprMacro(),
            new NestedDataExpressions.JsonValueExprMacro(),
//            new NestedDataExpressions.ParseJsonExprMacro(),
//            new NestedDataExpressions.ToJsonStringExprMacro(),
//            new NestedDataExpressions.TryParseJsonExprMacro(),
//            new NestedDataExpressions(),

            new LookupExprMacro(new LookupExtractorFactoryContainerProvider()
            {
              @Override
              public Set<String> getAllLookupNames()
              {
                return null;
              }

              @Override
              public Optional<LookupExtractorFactoryContainer> get(String s)
              {
                return Optional.empty();
              }
            })

        )
    );
  }

}