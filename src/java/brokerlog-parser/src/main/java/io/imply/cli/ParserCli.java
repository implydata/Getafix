package io.imply.cli;

import com.google.inject.Injector;
import com.google.inject.Module;
import org.apache.druid.cli.CliBroker;
import org.apache.druid.guice.GuiceInjectors;

import java.util.List;

public class ParserCli extends CliBroker
{
   public List<? extends Module> getModules(){
     return super.getModules();
   }
}
